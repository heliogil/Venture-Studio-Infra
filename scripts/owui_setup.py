"""
Setup Open WebUI: criar modelo personalizado com system prompt do Venture Studio.
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


def post(path, data, token=None):
    headers = {"Content-Type": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    req = urllib.request.Request(
        BASE + path,
        data=json.dumps(data).encode(),
        headers=headers,
        method="POST",
    )
    try:
        with urllib.request.urlopen(req) as r:
            return r.status, json.loads(r.read())
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode()


def get(path, token):
    req = urllib.request.Request(
        BASE + path,
        headers={"Authorization": f"Bearer {token}"},
        method="GET",
    )
    try:
        with urllib.request.urlopen(req) as r:
            return r.status, json.loads(r.read())
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode()


# 1. Login
status, resp = post("/api/v1/auths/signin", {"email": EMAIL, "password": PASSWORD})
token = resp.get("token") if isinstance(resp, dict) else None
print(f"Login: {status} | role={resp.get('role') if isinstance(resp, dict) else 'ERR'}")
if not token:
    print("Falha no login:", resp)
    exit(1)

# 2. Criar modelo com system prompt
status, resp = post(
    "/api/v1/models/create",
    {
        "id": "assistente-vs",
        "name": "Assistente VS",
        "base_model_id": "Geral",
        "params": {"system": SYSTEM_PROMPT},
        "meta": {
            "description": "Assistente pessoal do Hélio Gil — Venture Studio",
            "profile_image_url": "",
        },
    },
    token,
)
print(f"Criar modelo: {status} | {str(resp)[:150]}")

# 3. Se endpoint acima não existir, tentar /api/v1/models
if status not in (200, 201):
    status, resp = post(
        "/api/v1/models",
        {
            "id": "assistente-vs",
            "name": "Assistente VS",
            "base_model_id": "Geral",
            "params": {"system": SYSTEM_PROMPT},
            "meta": {"description": "Assistente pessoal do Hélio Gil — Venture Studio"},
        },
        token,
    )
    print(f"Criar modelo (alt): {status} | {str(resp)[:150]}")

# 4. Desactivar signup
status, resp = post(
    "/api/v1/auths/signup/enabled",
    {"enabled": False},
    token,
)
print(f"Disable signup: {status} | {str(resp)[:100]}")

# 5. Verificar modelos disponíveis
status, resp = get("/api/v1/models", token)
if isinstance(resp, dict):
    models = [m.get("id") or m.get("name") for m in resp.get("data", [])]
    print(f"Modelos visíveis: {models}")
