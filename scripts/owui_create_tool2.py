"""
Criar tool vault_search no Open WebUI.
"""
import urllib.request
import urllib.error
import json

BASE = "http://localhost:3000"
EMAIL = "heliogil@gmail.com"
PASSWORD = "Gracindo0!"

# Open WebUI requires tools inside a Tools class
TOOL_CODE = """\
import requests

class Tools:
    def search_vault(self, query: str) -> str:
        \"\"\"
        Pesquisa o vault de conhecimento pessoal do Helio Gil (notas Obsidian).
        Use sempre que precisar de contexto sobre projectos, ideias, decisoes passadas,
        infra, aprendizados, cursos ou qualquer informacao nas notas do utilizador.
        :param query: O que pesquisar no vault (em portugues)
        :return: Trechos relevantes com a fonte de cada um
        \"\"\"
        try:
            resp = requests.post(
                "http://knowledge_api:8000/search",
                json={"query": query, "limit": 4, "score_threshold": 0.45},
                timeout=15
            )
            results = resp.json()
            if not results:
                return "Nenhum resultado encontrado no vault para essa pesquisa."
            output = "Notas relevantes encontradas no vault:\\n\\n"
            for r in results:
                title = r.get("title", "Sem titulo")
                score = r.get("score", 0)
                snippet = r.get("content_snippet", "")
                source = r.get("source_path", "")
                output += f"**{title}** (relevancia: {score:.0%})\\n{snippet}\\nFonte: {source}\\n\\n"
            return output
        except Exception as e:
            return f"Erro ao pesquisar vault: {e}"
"""


def req(method, path, data=None, token=None):
    headers = {"Content-Type": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    r = urllib.request.Request(
        BASE + path,
        data=json.dumps(data).encode() if data else None,
        headers=headers,
        method=method,
    )
    try:
        with urllib.request.urlopen(r) as resp:
            raw = resp.read()
            try:
                return resp.status, json.loads(raw)
            except Exception:
                return resp.status, raw.decode()
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode()


_, resp = req("POST", "/api/v1/auths/signin", {"email": EMAIL, "password": PASSWORD})
token = resp["token"]
print(f"Login OK | role={resp['role']}")

status, resp = req(
    "POST",
    "/api/v1/tools/create",
    {
        "id": "vault_search",
        "name": "Vault Search",
        "description": "Pesquisa vault Obsidian do Helio Gil — contexto pessoal e projectos",
        "content": TOOL_CODE,
        "meta": {"description": "RAG sobre vault pessoal via knowledge_api"},
    },
    token,
)
print(f"Create tool: {status} | {str(resp)[:300]}")
