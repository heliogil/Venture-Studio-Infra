-- Executado automaticamente no container knowledge_db ao iniciar
-- Base de dados: knowledge

CREATE EXTENSION IF NOT EXISTS vector;

-- Documentos indexados do vault Obsidian
CREATE TABLE IF NOT EXISTS documents (
  id               SERIAL PRIMARY KEY,
  source_path      TEXT UNIQUE NOT NULL,
  title            TEXT,
  content          TEXT NOT NULL,
  embedding        vector(768),
  metadata         JSONB DEFAULT '{}',
  indexed_at       TIMESTAMPTZ DEFAULT NOW(),
  file_modified_at TIMESTAMPTZ
);

-- Índice para busca semântica
CREATE INDEX IF NOT EXISTS idx_documents_embedding
  ON documents USING ivfflat (embedding vector_cosine_ops)
  WITH (lists = 50);

CREATE INDEX IF NOT EXISTS idx_documents_path
  ON documents (source_path);
