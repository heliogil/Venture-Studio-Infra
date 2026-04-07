"""
Delete assistente-vs e recriar como Jarvis Candango.
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
            return resp.status, json.loads(resp.read())
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode()


# Login
_, resp = req("POST", "/api/v1/auths/signin", {"email": EMAIL, "password": PASSWORD})
token = resp["token"]
print(f"Login OK")

# Delete old model
status, resp = req("DELETE", "/api/v1/models/assistente-vs", token=token)
print(f"Delete assistente-vs: {status} | {str(resp)[:80]}")

# Recreate with correct name and ID
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
            "profile_image_url": "",
        },
    },
    token,
)
print(f"Create Jarvis Candango: {status} | {str(resp)[:150]}")

# List models to confirm
status, resp = req("GET", "/api/v1/models", token=token)
if isinstance(resp, dict):
    names = [m.get("name") for m in resp.get("data", [])]
    print(f"Modelos: {names}")
