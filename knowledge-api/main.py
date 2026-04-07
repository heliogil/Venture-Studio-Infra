"""
knowledge-api/main.py
API de RAG sobre o vault Obsidian (pgvector + nomic-embed-text via Ollama).
Endpoints: GET /health, POST /search, POST /index, DELETE /index/{path}
"""
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import psycopg2
import psycopg2.extras
import httpx
import os
import json
import logging
from typing import List, Optional

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="Knowledge API", version="1.0.0")

DATABASE_URL = os.environ["DATABASE_URL"]
OLLAMA_URL = os.environ.get("OLLAMA_URL", "http://vs_ollama:11434")
EMBED_MODEL = "nomic-embed-text"


def get_conn():
    return psycopg2.connect(DATABASE_URL)


async def embed(text: str) -> List[float]:
    """Gera embedding via Ollama (nomic-embed-text, 768 dimensões)."""
    async with httpx.AsyncClient(timeout=60) as http:
        resp = await http.post(
            f"{OLLAMA_URL}/api/embed",
            json={"model": EMBED_MODEL, "input": text[:8000]},
        )
        resp.raise_for_status()
        return resp.json()["embeddings"][0]


class SearchRequest(BaseModel):
    query: str
    limit: int = 5
    score_threshold: float = 0.50
    mode: str = "hybrid"  # "semantic" | "keyword" | "hybrid"


class IndexRequest(BaseModel):
    source_path: str
    title: Optional[str] = None
    content: str
    metadata: dict = {}


class SearchResult(BaseModel):
    source_path: str
    title: Optional[str]
    content_snippet: str
    score: float


@app.get("/health")
def health():
    return {"status": "ok", "embed_model": EMBED_MODEL}


@app.post("/search", response_model=List[SearchResult])
async def search(req: SearchRequest):
    if not req.query.strip():
        raise HTTPException(status_code=400, detail="Query vazia")

    conn = get_conn()
    try:
        cur = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)

        if req.mode == "keyword":
            # Busca por palavras-chave exactas (tsvector)
            cur.execute(
                """
                SELECT source_path, title, content,
                       ts_rank(fts, plainto_tsquery('portuguese', %s)) AS score
                FROM documents
                WHERE fts @@ plainto_tsquery('portuguese', %s)
                ORDER BY score DESC
                LIMIT %s
                """,
                (req.query, req.query, req.limit),
            )
            rows = cur.fetchall()
            results = []
            for row in rows:
                score = float(row["score"])
                if score < 0.01:
                    continue
                results.append(SearchResult(
                    source_path=row["source_path"],
                    title=row["title"],
                    content_snippet=row["content"][:500],
                    score=round(min(score, 1.0), 4),
                ))
            return results

        # Semântica (sempre necessária para hybrid e semantic)
        embedding = await embed(req.query)
        vec = json.dumps(embedding)

        if req.mode == "semantic":
            cur.execute(
                """
                SELECT source_path, title, content,
                       1 - (embedding <=> %s::vector) AS score
                FROM documents
                WHERE embedding IS NOT NULL
                ORDER BY embedding <=> %s::vector
                LIMIT %s
                """,
                (vec, vec, req.limit * 2),
            )
            rows = cur.fetchall()

        else:  # hybrid — semântica + keyword, re-ranked
            cur.execute(
                """
                SELECT source_path, title, content,
                       (1 - (embedding <=> %s::vector)) AS sem_score,
                       COALESCE(ts_rank(fts, plainto_tsquery('portuguese', %s)), 0) AS kw_score
                FROM documents
                WHERE embedding IS NOT NULL
                ORDER BY
                    (0.7 * (1 - (embedding <=> %s::vector)) +
                     0.3 * COALESCE(ts_rank(fts, plainto_tsquery('portuguese', %s)), 0)) DESC
                LIMIT %s
                """,
                (vec, req.query, vec, req.query, req.limit * 2),
            )
            rows = cur.fetchall()

    finally:
        conn.close()

    results = []
    for row in rows:
        score = float(row["score"] if req.mode == "semantic" else
                      0.7 * float(row["sem_score"]) + 0.3 * float(row["kw_score"]))
        if score < req.score_threshold:
            continue
        results.append(SearchResult(
            source_path=row["source_path"],
            title=row["title"],
            content_snippet=row["content"][:500],
            score=round(score, 4),
        ))
        if len(results) >= req.limit:
            break

    return results


@app.post("/index")
async def index_document(req: IndexRequest):
    if not req.content.strip():
        raise HTTPException(status_code=400, detail="Content vazio")

    embedding = await embed(req.content)

    conn = get_conn()
    try:
        cur = conn.cursor()
        cur.execute(
            """
            INSERT INTO documents (source_path, title, content, embedding, metadata)
            VALUES (%s, %s, %s, %s::vector, %s)
            ON CONFLICT (source_path) DO UPDATE
            SET title      = EXCLUDED.title,
                content    = EXCLUDED.content,
                embedding  = EXCLUDED.embedding,
                metadata   = EXCLUDED.metadata,
                indexed_at = NOW()
            """,
            (
                req.source_path,
                req.title,
                req.content,
                json.dumps(embedding),
                json.dumps(req.metadata),
            ),
        )
        conn.commit()
    finally:
        conn.close()

    logger.info(f"Indexed: {req.source_path}")
    return {"indexed": req.source_path, "status": "ok"}


@app.delete("/index/{doc_path:path}")
def delete_document(doc_path: str):
    conn = get_conn()
    try:
        cur = conn.cursor()
        cur.execute("DELETE FROM documents WHERE source_path = %s", (doc_path,))
        deleted = cur.rowcount
        conn.commit()
    finally:
        conn.close()
    return {"deleted": deleted, "source_path": doc_path}
