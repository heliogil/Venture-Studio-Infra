"""
Actualizar params do Jarvis Candango: temperatura + num_ctx para compressão de contexto.
"""
import sqlite3
import json

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

db = "/app/backend/data/webui.db"
conn = sqlite3.connect(db)
cur = conn.cursor()

# Update Jarvis model params
params = {
    "system": SYSTEM_PROMPT,
    "temperature": 0.7,       # Mais focado, menos verbose = menos tokens
    "max_tokens": 1500,        # Limite por resposta (evita respostas enormes)
    "num_ctx": 8192,           # Janela de contexto razoável
}

cur.execute(
    "UPDATE model SET params=? WHERE id=?",
    (json.dumps(params, ensure_ascii=False), "jarvis-candango")
)
conn.commit()

# Verify
cur.execute("SELECT params FROM model WHERE id='jarvis-candango'")
row = cur.fetchone()
if row:
    p = json.loads(row[0])
    print("Updated params:")
    for k, v in p.items():
        if k != "system":
            print(f"  {k}: {v}")
    print(f"  system: [{len(p.get('system',''))} chars]")

conn.close()
print("Done")
