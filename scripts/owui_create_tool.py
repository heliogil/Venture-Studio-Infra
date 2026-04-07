"""
Criar tool "vault_search" no Open WebUI.
O Jarvis Candango chama esta tool automaticamente quando precisa de contexto do vault.
"""
import urllib.request
import urllib.error
import json

BASE = "http://localhost:3000"
EMAIL = "heliogil@gmail.com"
PASSWORD = "Gracindo0!"

TOOL_CODE = '''
import requests

def search_vault(query: str) -> str:
    """
    Pesquisa o vault de conhecimento pessoal do Hélio Gil (notas Obsidian).
    Use esta tool sempre que precisar de contexto sobre: projectos, ideias,
    decisões passadas, notas pessoais, infra, aprendizados, cursos, ou
    qualquer informação que possa estar nas notas do utilizador.
    :param query: O que pesquisar no vault (em português)
    :return: Trechos relevantes do vault com a fonte de cada um
    """
    try:
        resp = requests.post(
            "http://knowledge_api:8000/search",
            json={"query": query, "limit": 4, "score_threshold": 0.45},
            timeout=15
        )
        results = resp.json()
        if not results:
            return "Nenhum resultado encontrado no vault para essa pesquisa."

        output = f"Encontrei {len(results)} nota(s) relevante(s) no vault:\\n\\n"
        for r in results:
            output += f"**{r['title']}** (relevância: {r['score']:.0%})\\n"
            output += f"{r['content_snippet']}\\n"
            output += f"_Fonte: {r['source_path']}_\\n\\n"
        return output
    except Exception as e:
        return f"Erro ao pesquisar vault: {e}"
'''


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
            return resp.status, json.loads(resp.read())
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode()


# Login
_, resp = req("POST", "/api/v1/auths/signin", {"email": EMAIL, "password": PASSWORD})
token = resp["token"]
print(f"Login OK | role={resp['role']}")

# Create tool
status, resp = req(
    "POST",
    "/api/v1/tools/create",
    {
        "name": "Vault Search",
        "description": "Pesquisa o vault de notas do Hélio Gil (Obsidian). Usar para contexto pessoal, projectos, ideias e decisões.",
        "content": TOOL_CODE,
        "meta": {"description": "Pesquisa semântica no vault Obsidian via knowledge_api"},
    },
    token,
)
print(f"Create tool: {status} | {str(resp)[:200]}")

# List tools to confirm
status, resp = req("GET", "/api/v1/tools", token=token)
if isinstance(resp, list):
    for t in resp:
        print(f"Tool: id={t.get('id')} name={t.get('name')}")
