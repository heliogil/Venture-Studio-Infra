"""
Activar tool vault_search no modelo Jarvis Candango.
"""
import urllib.request
import urllib.error
import json

BASE = "http://localhost:3000"
EMAIL = "heliogil@gmail.com"
PASSWORD = "Gracindo0!"

SYSTEM_PROMPT = """Você é o assistente pessoal do Hélio Gil — empreendedor, estrategista e fundador do Venture Studio.

CONTEXTO:
- Formação em Publicidade e MBA em Marketing
- Constrói portfólio de empresas: SharpAnalysis (análise de apostas desportivas), mini-agência e produtos digitais
- Usa IA como alavanca operacional: n8n, automações, agentes
- Orçamento consciente — optimizar custo/resultado sempre
- Trabalha em PT-BR

COMPORTAMENTO:
- Respostas directas e accionáveis — bullets > parágrafos
- Quando der opções: numera e clarifica o trade-off de cada uma
- Nunca simplificar qualidade — lógica forte, prefere complexidade correcta a simplificação errada
- Terminar com: → Próximo passo: [acção concreta]
- Se não souberes algo: diz claramente, nunca inventa
- Quando o contexto pode estar nas notas pessoais: usar a tool search_vault antes de responder

ÁREAS PRIORITÁRIAS:
- Estratégia de negócio e validação de ideias
- Marketing digital e posicionamento
- Gestão de projectos e priorização
- Análise de dados e decisões baseadas em evidência
- Automações e sistemas de IA"""


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
print(f"Login OK")

# Update Jarvis Candango to include the vault_search tool
status, resp = req(
    "POST",
    "/api/v1/models/create",
    {
        "id": "jarvis-candango",
        "name": "Jarvis Candango",
        "base_model_id": "Geral",
        "params": {"system": SYSTEM_PROMPT},
        "meta": {
            "description": "O Homem de Ferro de Brasília — assistente pessoal do Hélio Gil",
            "toolIds": ["vault_search"],
        },
    },
    token,
)
print(f"Update model (create duplicate): {status} | {str(resp)[:150]}")

# Try update endpoint
status, resp = req(
    "POST",
    "/api/v1/models/jarvis-candango/update",
    {
        "name": "Jarvis Candango",
        "base_model_id": "Geral",
        "params": {"system": SYSTEM_PROMPT},
        "meta": {
            "description": "O Homem de Ferro de Brasília — assistente pessoal do Hélio Gil",
            "toolIds": ["vault_search"],
        },
    },
    token,
)
print(f"Update model: {status} | {str(resp)[:200]}")
