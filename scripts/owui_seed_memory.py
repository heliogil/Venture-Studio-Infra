"""
Seed de memórias iniciais para o Jarvis Candango.
Factos permanentes sobre o Hélio e o Venture Studio.
"""
import urllib.request
import urllib.error
import json

BASE = "http://localhost:3000"
EMAIL = "heliogil@gmail.com"
PASSWORD = "Gracindo0!"

MEMORIES = [
    "Hélio Gil é empreendedor de Brasília, formação em Publicidade e MBA em Marketing.",
    "Hélio prefere respostas em PT-BR, concisas, em bullets. Evitar parágrafos longos.",
    "Venture Studio é o nome do projecto de holding de Hélio: portfólio de empresas e produtos digitais.",
    "SharpAnalysis é o primeiro produto do Venture Studio: análise de dados desportivos para apostas pre-match. Stack: n8n + PostgreSQL + Docker.",
    "Orçamento total do Venture Studio: R$500/mês de infra. VPS Contabo: 37.60.236.227.",
    "Hélio usa n8n, automações, agentes IA e Windsurf como ferramentas operacionais. Não é programador mas tem lógica forte.",
    "Modelos disponíveis: Rapido (triagem), Geral (workhorse), Coder (código), Revisor (Claude Sonnet), Nuclear (Claude Opus).",
    "O vault Obsidian de Hélio está sincronizado com Dropbox em /Aplicativos/remotely-save/Hélio Gil e indexado no knowledge_api com pgvector.",
    "Hélio prefere receber opções numeradas com trade-offs claros quando há múltiplas abordagens.",
    "Terminar respostas com '→ Próximo passo:' quando houver acção concreta a tomar.",
]


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
print(f"Login OK | user_id={resp.get('id')}")

ok = err = 0
for mem in MEMORIES:
    status, resp = req("POST", "/api/v1/memories/add", {"content": mem}, token)
    if status == 200:
        ok += 1
        print(f"  OK {mem[:60]}...")
    else:
        err += 1
        print(f"  FAIL {status}: {str(resp)[:80]}")

print(f"\nDone: {ok} memories added, {err} errors")
