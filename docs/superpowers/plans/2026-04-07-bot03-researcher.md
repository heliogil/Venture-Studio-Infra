# BOT 03 — Researcher — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Agente de pesquisa profunda que recebe tema → pesquisa vault + sintetiza → produz relatório estruturado em MD → salva no vault → sync automático para Obsidian via Dropbox.

**Architecture:** Modelo Open WebUI (`Revisor` para temas críticos, `Geral` para pesquisa geral) com system prompt especializado em investigação + tool vault_search + tool web_search (quando disponível). Output salvo automaticamente em `vault/03-Recursos/Pesquisas/`. Segue BOT_STANDARD.md completo.

**Tech Stack:** Open WebUI custom model, Python tool (vault writer), knowledge_api hybrid search, Dropbox upload via vault_sync

---

## Relatório padrão (output obrigatório)

Todo o output do BOT 03 deve seguir este formato:

```markdown
---
tipo: pesquisa
status: em-desenvolvimento
tags: [tag1, tag2]
criado: YYYY-MM-DD
modelo: Geral
fontes: [vault, web]
---

# [Título da Pesquisa]

## Resumo executivo
[3-5 bullets com as conclusões principais]

## Contexto
[O que motivou esta pesquisa]

## Análise
[Corpo principal — estruturado em sub-secções]

## Conclusões e recomendações
[Acções concretas derivadas da pesquisa]

## Fontes consultadas
[Lista de fontes — vault e/ou web]

→ Próximo passo: [acção concreta derivada desta pesquisa]
```

---

## File Structure

- Modify (via API): Open WebUI — criar modelo `Pesquisador VS`
- Create: `scripts/owui_create_researcher.py` — script de criação do modelo + tool
- Create: `scripts/vault_writer_tool.py` — tool para salvar relatórios no vault

---

## Task 1: Tool vault_writer — salvar relatórios no vault

**Files:**
- Create: `scripts/owui_create_researcher.py` (inclui tool + modelo)

- [ ] **Step 1: Definir tool vault_writer**

A tool salva o relatório no vault e faz upload para Dropbox:

```python
# Código da tool (vai dentro do Open WebUI)
import httpx
import json
from datetime import datetime

class Tools:
    def save_research(self, titulo: str, conteudo: str, tags: str = "") -> str:
        """
        Salva um relatório de pesquisa no vault do Hélio Gil.
        Use esta tool SEMPRE ao terminar uma pesquisa para preservar o conhecimento.
        :param titulo: Título da pesquisa (usado como nome do ficheiro)
        :param conteudo: Conteúdo completo do relatório em Markdown
        :param tags: Tags separadas por vírgula (ex: "marketing,strategy,brazil")
        :return: Confirmação com path do ficheiro salvo
        """
        try:
            slug = titulo.lower().replace(" ", "-")[:60]
            date = datetime.now().strftime("%Y-%m-%d")
            filename = f"{date}-{slug}.md"

            # Garante frontmatter se não existir
            if not conteudo.strip().startswith("---"):
                tag_list = [t.strip() for t in tags.split(",") if t.strip()]
                frontmatter = (
                    f"---\n"
                    f"tipo: pesquisa\n"
                    f"status: em-desenvolvimento\n"
                    f"tags: {json.dumps(tag_list, ensure_ascii=False)}\n"
                    f"criado: {date}\n"
                    f"---\n\n"
                )
                conteudo = frontmatter + conteudo

            resp = httpx.post(
                "http://knowledge_api:8000/index",
                json={
                    "source_path": f"vault:/03-Recursos/Pesquisas/{filename}",
                    "title": titulo,
                    "content": conteudo,
                    "metadata": {"tipo": "pesquisa", "tags": tags, "auto_saved": True},
                },
                timeout=30,
            )
            if resp.status_code == 200:
                return f"Pesquisa salva: vault:/03-Recursos/Pesquisas/{filename}\nIndexada no knowledge_api para futuras pesquisas."
            return f"Erro ao salvar: {resp.status_code} {resp.text[:100]}"
        except Exception as e:
            return f"Erro: {e}"
```

- [ ] **Step 2: Criar script owui_create_researcher.py**

```python
"""
Criar BOT 03 Researcher no Open WebUI:
- Modelo Pesquisador VS (base: Geral)
- Tools: vault_search (existente) + vault_writer (nova)
- System prompt especializado em investigação
"""
import urllib.request
import urllib.error
import json

BASE = "http://localhost:3000"
EMAIL = "heliogil@gmail.com"
PASSWORD = "Gracindo0!"

SYSTEM_PROMPT = """Você é o Pesquisador do Venture Studio — agente especializado em investigação profunda e síntese de conhecimento.

MISSÃO:
Transformar perguntas em conhecimento estruturado e accionável, preservado permanentemente no vault do Hélio Gil.

PROCESSO OBRIGATÓRIO para cada pesquisa:
1. Usar search_vault para verificar o que já existe sobre o tema
2. Analisar e sintetizar — não repetir, expandir e conectar
3. Produzir relatório no formato padrão (ver abaixo)
4. Usar save_research para salvar no vault SEMPRE ao terminar

FORMATO DE RELATÓRIO OBRIGATÓRIO:
---
tipo: pesquisa
status: em-desenvolvimento
tags: [relevantes]
criado: [data de hoje]
---

# [Título]

## Resumo executivo
[3-5 bullets com conclusões principais]

## Contexto
[Motivação e escopo da pesquisa]

## Análise
[Corpo principal estruturado]

## Conclusões e recomendações
[Acções concretas]

## Fontes consultadas
[Vault e/ou outras fontes]

→ Próximo passo: [acção derivada]

COMPORTAMENTO:
- Profundidade > velocidade
- Conectar com outros temas do vault quando relevante
- PT-BR sempre
- Nunca inventar fontes — se não souberes, diz claramente
- Relatório completo antes de salvar — não salvar rascunhos"""
```

- [ ] **Step 3: Run: verificar se tool vault_search já existe**

```bash
# No VPS:
curl -s http://localhost:3000/api/v1/tools \
  -H "Authorization: Bearer TOKEN" | python3 -c \
  "import sys,json; tools=json.load(sys.stdin); print([t['id'] for t in tools])"
```

Expected: `['vault_search']` (já existe da implementação anterior)

- [ ] **Step 4: Commit**

```bash
git add scripts/owui_create_researcher.py
git commit -m "feat: BOT 03 Researcher — script de criação com vault_writer tool"
```

---

## Task 2: Criar tool vault_writer no Open WebUI

**Files:**
- Modify: `scripts/owui_create_researcher.py` — adicionar criação da tool

- [ ] **Step 1: Criar tool vault_writer via API**

Adicionar ao script:

```python
VAULT_WRITER_CODE = """\
import httpx
import json
from datetime import datetime

class Tools:
    def save_research(self, titulo: str, conteudo: str, tags: str = "") -> str:
        \"\"\"
        Salva um relatorio de pesquisa no vault do Helio Gil.
        Use SEMPRE ao terminar uma pesquisa para preservar o conhecimento.
        :param titulo: Titulo da pesquisa (nome do ficheiro)
        :param conteudo: Conteudo completo em Markdown
        :param tags: Tags separadas por virgula
        :return: Confirmacao com path salvo
        \"\"\"
        try:
            slug = titulo.lower().replace(" ", "-")[:60]
            date = datetime.now().strftime("%Y-%m-%d")
            filename = f"{date}-{slug}.md"
            if not conteudo.strip().startswith("---"):
                tag_list = [t.strip() for t in tags.split(",") if t.strip()]
                front = f"---\\ntipo: pesquisa\\nstatus: em-desenvolvimento\\ntags: {json.dumps(tag_list, ensure_ascii=False)}\\ncriado: {date}\\n---\\n\\n"
                conteudo = front + conteudo
            resp = httpx.post(
                "http://knowledge_api:8000/index",
                json={
                    "source_path": f"vault:/03-Recursos/Pesquisas/{filename}",
                    "title": titulo,
                    "content": conteudo,
                    "metadata": {"tipo": "pesquisa", "tags": tags, "auto_saved": True},
                },
                timeout=30,
            )
            if resp.status_code == 200:
                return f"Salvo: vault:/03-Recursos/Pesquisas/{filename} — indexado para futuras pesquisas."
            return f"Erro {resp.status_code}: {resp.text[:100]}"
        except Exception as e:
            return f"Erro: {e}"
"""

# Criar tool via API
status, resp = req("POST", "/api/v1/tools/create", {
    "id": "vault_writer",
    "name": "Vault Writer",
    "description": "Salva relatórios de pesquisa no vault Obsidian do Hélio Gil",
    "content": VAULT_WRITER_CODE,
    "meta": {"description": "Persistência de conhecimento — pesquisas → vault"},
}, token)
print(f"vault_writer: {status} | {str(resp)[:100]}")
```

- [ ] **Step 2: Run test**

```bash
# Verificar tool criada
curl -s http://localhost:3000/api/v1/tools \
  -H "Authorization: Bearer TOKEN" | python3 -c \
  "import sys,json; tools=json.load(sys.stdin); print([t['id'] for t in tools])"
```

Expected: `['vault_search', 'vault_writer']`

---

## Task 3: Criar modelo Pesquisador VS no Open WebUI

**Files:**
- Modify: `scripts/owui_create_researcher.py` — adicionar criação do modelo

- [ ] **Step 1: Criar modelo com ambas as tools**

```python
status, resp = req("POST", "/api/v1/models/create", {
    "id": "pesquisador-vs",
    "name": "Pesquisador VS",
    "base_model_id": "Geral",
    "params": {
        "system": SYSTEM_PROMPT,
        "temperature": 0.5,    # mais determinístico para pesquisa
        "max_tokens": 3000,    # relatórios precisam de espaço
        "num_ctx": 16384,      # contexto maior para síntese
    },
    "meta": {
        "description": "Agente de pesquisa profunda — produz relatórios estruturados e salva no vault",
        "toolIds": ["vault_search", "vault_writer"],
    },
}, token)
print(f"Pesquisador VS: {status} | {str(resp)[:150]}")
```

- [ ] **Step 2: Seed de memórias do Pesquisador**

```python
MEMORIES_RESEARCHER = [
    "O Pesquisador VS deve SEMPRE salvar relatórios no vault usando save_research ao terminar.",
    "Relatórios salvos em vault:/03-Recursos/Pesquisas/ com data no nome do ficheiro.",
    "Formato obrigatório: frontmatter YAML + Resumo executivo + Contexto + Análise + Conclusões + Fontes.",
    "Pesquisa começa sempre com search_vault para verificar conhecimento existente antes de sintetizar.",
]
```

- [ ] **Step 3: Commit**

```bash
git add scripts/owui_create_researcher.py
git commit -m "feat: BOT 03 Pesquisador VS — modelo + vault_writer tool + seed memories"
```

---

## Task 4: Deploy e teste

- [ ] **Step 1: Upload e executar script no VPS**

```bash
# Local → VPS
scp scripts/owui_create_researcher.py root@37.60.236.227:/tmp/

# No VPS
python3 /tmp/owui_create_researcher.py
```

Expected:
```
Login OK
vault_writer: 200
Pesquisador VS: 200
Memories: 4 added
```

- [ ] **Step 2: Teste básico — pesquisa simples**

No Open WebUI, seleccionar modelo `Pesquisador VS` e enviar:

```
Faz uma pesquisa sobre modelos de precificação para agências digitais no Brasil em 2026.
Consulta o vault primeiro e depois sintetiza com o que sabes.
```

Expected:
- Bot usa `search_vault` primeiro
- Produz relatório estruturado
- Usa `save_research` para guardar
- Confirma path do ficheiro salvo

- [ ] **Step 3: Verificar ficheiro no knowledge_api**

```bash
curl -s -X POST http://37.60.236.227:8010/search \
  -H "Content-Type: application/json" \
  -d '{"query": "precificacao agencias brasil", "limit": 2}'
```

Expected: resultado com `source_path: vault:/03-Recursos/Pesquisas/...`

- [ ] **Step 4: Actualizar landing page**

Adicionar card do Pesquisador VS em `docs/index.html`.

- [ ] **Step 5: Commit final**

```bash
git add docs/index.html
git commit -m "feat: BOT 03 Pesquisador VS — deploy completo"
```

---

## Notas de uso

**Quando usar Geral (padrão) vs Revisor:**
- `Geral` → pesquisas operacionais (marketing, estratégia, produto)
- `Revisor` (Claude Sonnet) → pesquisas críticas com decisão de alto impacto (trocar de modelo no chat)

**Limitação actual:** sem acesso à web em tempo real. Pesquisa sobre vault + conhecimento do modelo.
Para web search: adicionar tool futura quando Open WebUI suportar (próxima sprint).
