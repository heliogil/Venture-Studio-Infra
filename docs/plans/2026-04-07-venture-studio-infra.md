# Venture Studio — Infraestrutura de Venture Building com IA

> **Para agentes:** REQUIRED SUB-SKILL: Use `superpowers:subagent-driven-development` (recomendado) ou `superpowers:executing-plans` para implementar task-by-task. Steps usam `- [ ]` para tracking.

**Goal:** Montar a infra-mãe de venture building: LiteLLM como router de modelos com custo controlado, Open WebUI como interface principal do BOT 01 (assistente pessoal), Discord bridge para acesso móvel, e Knowledge Engine com RAG sobre o vault Obsidian — tudo em Docker no VPS Contabo, orçamento ≤ R$500/mês total.

**Architecture:** Hybrid. BOT 01 = Open WebUI → LiteLLM → OpenRouter (sem código Python extra, só config + system prompt). BOT 02/03/05 = serviços Python FastAPI independentes no mesmo VPS. Redis para filas. `knowledge_db` com pgvector isolado do `sharp_db` (porta 5433). OpenClaw mantém papel de workspace de pesquisa com browser. Discord = acesso móvel assíncrono.

**Tech Stack:** Docker Compose, LiteLLM (proxy OpenAI-compatible + budget tracking), Open WebUI (chat UI self-hosted), PostgreSQL 16 + pgvector (`knowledge_db`), Redis 7-alpine, Ollama (embeddings local gratuito), FastAPI + Python 3.12, discord.py 2.x, Dramatiq + APScheduler (workers).

**VPS:** `root@37.60.236.227` | `/opt/venture-studio/`
**Repo local:** `F:\projects\venture-studio` → push → `git pull` no VPS

---

## Budget & Modelos

> ⚠️ Verificar slugs exactos em openrouter.ai/models antes de implementar — modelos actualizam.

| Alias LiteLLM | Modelo OpenRouter | Função | $/1M in | Est. mês |
|---------------|-------------------|--------|---------|---------|
| `cheap` | `google/gemini-flash-1.5-8b` | Triagem, FAQ, formatação, glue | $0.037 | ~$0.10 |
| `workhorse` | `qwen/qwen3-235b-a22b` | BOT 01 default: pesquisa, síntese, planeamento, escrita | $0.14 | ~$0.50 |
| `coder` | `deepseek/deepseek-r1` | BOT 02: código, debug, arquitectura técnica | $0.55 | ~$0.30 |
| `review` | `anthropic/claude-sonnet-4-6` | Revisão crítica — gatilho manual | $3.00 | ~$0.30 |
| `nuclear` | `anthropic/claude-opus-4-6` | Arquitectura fundacional — gatilho explícito | $15.00 | $0 |
| **TOTAL** | | | | **~$1.20/mês** |

Budget diário LiteLLM: US$2 (muito liberal — alertas sem bloquear).

---

## Mapeamento de Ficheiros

### Novo repositório: `F:\projects\venture-studio`

```
F:\projects\venture-studio\
├── .gitignore
├── .env.example
├── docker-compose.yml
├── litellm/
│   └── config.yaml
├── knowledge-api/
│   ├── Dockerfile
│   ├── main.py                  ← FastAPI RAG (search + index)
│   ├── vault_sync.py            ← Dropbox → VPS sync loop
│   ├── requirements.txt
│   ├── schema.sql               ← pgvector schema
│   └── init-create-litellm-db.sh ← cria DB litellm no init
├── discord-bridge/
│   ├── Dockerfile
│   ├── bot.py                   ← /ask /code /status
│   └── requirements.txt
├── automation-runner/
│   ├── Dockerfile
│   ├── runner.py                ← Dramatiq + APScheduler
│   └── requirements.txt
└── docs/
    └── plans/
        └── 2026-04-07-venture-studio-infra.md  ← este ficheiro
```

---

## Phase 0 — Fundação

### Task 1: Criar repositório venture-studio

**Files:**
- Create: `F:\projects\venture-studio\.gitignore`
- Create: `F:\projects\venture-studio\.env.example`

- [ ] **Step 1: Criar repo local**

```bash
mkdir F:\projects\venture-studio
cd F:\projects\venture-studio
git init -b main
mkdir -p litellm knowledge-api discord-bridge automation-runner docs/plans
```

- [ ] **Step 2: Criar `.gitignore`**

```
.env
*.pyc
__pycache__/
*.log
.DS_Store
*.egg-info/
dist/
.venv/
```

- [ ] **Step 3: Criar `.env.example`**

```env
# ── OpenRouter ──────────────────────────────
OPENROUTER_API_KEY=your_openrouter_key_here

# ── LiteLLM ─────────────────────────────────
# Gerar: python -c "import secrets; print('sk-vs-' + secrets.token_hex(16))"
LITELLM_MASTER_KEY=sk-vs-xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx

# ── Knowledge DB (PostgreSQL + pgvector) ────
# Gerar: python -c "import secrets; print(secrets.token_hex(16))"
KNOWLEDGE_DB_PASS=strong_password_here

# ── Open WebUI ───────────────────────────────
# Gerar: python -c "import secrets; print(secrets.token_hex(32))"
WEBUI_SECRET_KEY=long_random_secret_here

# ── Discord ──────────────────────────────────
DISCORD_TOKEN=your_discord_bot_token_here
# ID do servidor: Discord → Settings → Right-click no servidor → Copy Server ID
DISCORD_GUILD_ID=your_discord_server_id_here

# ── Vault Obsidian (path no Dropbox) ────────
# Verificar path real: python3 dropbox_helper.py list --folder /
VAULT_DROPBOX_PATH=/Obsidian
```

- [ ] **Step 4: Copiar `.env.example` para `.env` e preencher**

```bash
cp .env.example .env
# Preencher OPENROUTER_API_KEY, gerar os outros com os comandos comentados
```

- [ ] **Step 5: Copiar este plano para o repo**

```bash
# Copiar este ficheiro para docs/plans/
copy "F:\projects\sharpanalysis\docs\superpowers\plans\2026-04-07-venture-studio-infra.md" "F:\projects\venture-studio\docs\plans\"
```

- [ ] **Step 6: Primeiro commit**

```bash
git add .gitignore .env.example docs/
git commit -m "chore: init venture-studio repo"
```

- [ ] **Step 7: Criar repo no GitHub e push**

Criar repo `venture-studio` em github.com (privado).

```bash
git remote add origin https://github.com/SEU_USER/venture-studio.git
git push -u origin main
```

- [ ] **Step 8: Clonar e configurar no VPS**

```bash
# No VPS via SSH
cd /opt
git clone https://github.com/SEU_USER/venture-studio.git
cd /opt/venture-studio
cp .env.example .env
nano .env  # preencher com os mesmos valores do .env local
```

---

### Task 2: Schema do knowledge_db

**Files:**
- Create: `knowledge-api/schema.sql`
- Create: `knowledge-api/init-create-litellm-db.sh`

- [ ] **Step 1: Criar `knowledge-api/schema.sql`**

```sql
-- Executado automaticamente no container knowledge_db ao iniciar
-- Base de dados: knowledge

CREATE EXTENSION IF NOT EXISTS vector;

-- Documentos indexados do vault Obsidian
CREATE TABLE IF NOT EXISTS documents (
  id            SERIAL PRIMARY KEY,
  source_path   TEXT UNIQUE NOT NULL,       -- ex: "vault:/Projetos/SharpAnalysis.md"
  title         TEXT,
  content       TEXT NOT NULL,
  embedding     vector(768),                -- nomic-embed-text = 768 dimensões
  metadata      JSONB DEFAULT '{}',
  indexed_at    TIMESTAMPTZ DEFAULT NOW(),
  file_modified_at TIMESTAMPTZ
);

-- Índice para busca semântica (IVFFlat, listas=50 bom até ~200k docs)
CREATE INDEX IF NOT EXISTS idx_documents_embedding
  ON documents USING ivfflat (embedding vector_cosine_ops)
  WITH (lists = 50);

-- Índice para lookup por path
CREATE INDEX IF NOT EXISTS idx_documents_path
  ON documents (source_path);
```

- [ ] **Step 2: Criar `knowledge-api/init-create-litellm-db.sh`**

```bash
#!/bin/bash
# Cria a base de dados 'litellm' para o LiteLLM usar (budget tracking)
# Este script roda no init do container PostgreSQL
set -e

psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname "$POSTGRES_DB" <<-EOSQL
    SELECT 'CREATE DATABASE litellm'
    WHERE NOT EXISTS (
        SELECT FROM pg_database WHERE datname = 'litellm'
    )\gexec
EOSQL

echo "Database 'litellm' ready."
```

```bash
# Tornar executável ANTES do commit
chmod +x knowledge-api/init-create-litellm-db.sh
```

- [ ] **Step 3: Commit**

```bash
git add knowledge-api/schema.sql knowledge-api/init-create-litellm-db.sh
git commit -m "feat: knowledge DB schema (pgvector + litellm DB init)"
```

---

### Task 3: docker-compose.yml + LiteLLM config

**Files:**
- Create: `docker-compose.yml`
- Create: `litellm/config.yaml`

- [ ] **Step 1: Criar `litellm/config.yaml`**

```yaml
model_list:
  # Barato — triagem, classificação, FAQ, formatação
  - model_name: cheap
    litellm_params:
      model: openrouter/google/gemini-flash-1.5-8b
      api_key: os.environ/OPENROUTER_API_KEY
      api_base: https://openrouter.ai/api/v1

  # Workhorse — BOT 01 default (pesquisa, síntese, planeamento, escrita)
  - model_name: workhorse
    litellm_params:
      model: openrouter/qwen/qwen3-235b-a22b
      api_key: os.environ/OPENROUTER_API_KEY
      api_base: https://openrouter.ai/api/v1

  # Coder — BOT 02 (código, debug, arquitectura técnica)
  - model_name: coder
    litellm_params:
      model: openrouter/deepseek/deepseek-r1
      api_key: os.environ/OPENROUTER_API_KEY
      api_base: https://openrouter.ai/api/v1

  # Review — revisão crítica, validação (gatilho manual)
  - model_name: review
    litellm_params:
      model: openrouter/anthropic/claude-sonnet-4-6
      api_key: os.environ/OPENROUTER_API_KEY
      api_base: https://openrouter.ai/api/v1

  # Nuclear — arquitectura fundacional (gatilho explícito apenas)
  - model_name: nuclear
    litellm_params:
      model: openrouter/anthropic/claude-opus-4-6
      api_key: os.environ/OPENROUTER_API_KEY
      api_base: https://openrouter.ai/api/v1

litellm_settings:
  # Budget diário global: US$2 (alerta, não bloqueia)
  max_budget: 2.0
  budget_duration: 1d
  store_model_in_db: true       # necessário para tracking de uso

router_settings:
  routing_strategy: simple-shuffle
  # Fallback automático se modelo indisponível
  fallbacks:
    - workhorse:
        - cheap
    - coder:
        - workhorse

general_settings:
  master_key: os.environ/LITELLM_MASTER_KEY
  database_url: os.environ/LITELLM_DATABASE_URL
  store_prompts_in_spend_logs: false   # privacidade
```

- [ ] **Step 2: Criar `docker-compose.yml`**

```yaml
# Venture Studio — Infrastructure
# Deploy: git push → git pull no VPS → docker compose up -d

services:

  # ── Knowledge Database (PostgreSQL 16 + pgvector) ───────────────
  knowledge_db:
    image: pgvector/pgvector:pg16
    container_name: vs_knowledge_db
    restart: unless-stopped
    ports:
      - "5433:5432"          # porta diferente do sharp_db (5432)
    environment:
      POSTGRES_USER: knowledge
      POSTGRES_PASSWORD: ${KNOWLEDGE_DB_PASS}
      POSTGRES_DB: knowledge
    volumes:
      - knowledge_db_data:/var/lib/postgresql/data
      # 00_ cria DB litellm; 01_ cria schema da knowledge API
      - ./knowledge-api/init-create-litellm-db.sh:/docker-entrypoint-initdb.d/00_litellm_db.sh
      - ./knowledge-api/schema.sql:/docker-entrypoint-initdb.d/01_schema.sql
    networks:
      - vs_network
    healthcheck:
      test: ["CMD", "pg_isready", "-U", "knowledge"]
      interval: 10s
      timeout: 5s
      retries: 5

  # ── Redis (queues + cache + locks) ──────────────────────────────
  redis:
    image: redis:7-alpine
    container_name: vs_redis
    restart: unless-stopped
    ports:
      - "6380:6379"          # diferente de 6379 caso redis local exista
    command: redis-server --appendonly yes
    volumes:
      - redis_data:/data
    networks:
      - vs_network
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 10s
      timeout: 5s
      retries: 5

  # ── LiteLLM (model router + cost tracking) ─────────────────────
  litellm:
    image: ghcr.io/berriai/litellm:main-latest
    container_name: vs_litellm
    restart: unless-stopped
    ports:
      - "4000:4000"          # NÃO expor ao exterior — só uso interno
    environment:
      OPENROUTER_API_KEY: ${OPENROUTER_API_KEY}
      LITELLM_MASTER_KEY: ${LITELLM_MASTER_KEY}
      # LiteLLM usa a DB litellm no mesmo container PostgreSQL
      LITELLM_DATABASE_URL: postgresql://knowledge:${KNOWLEDGE_DB_PASS}@knowledge_db:5432/litellm
    volumes:
      - ./litellm/config.yaml:/app/config.yaml
    command: ["--config", "/app/config.yaml", "--port", "4000", "--num_workers", "1"]
    depends_on:
      knowledge_db:
        condition: service_healthy
    networks:
      - vs_network

  # ── Open WebUI (BOT 01 — interface principal) ───────────────────
  open_webui:
    image: ghcr.io/open-webui/open-webui:main
    container_name: vs_open_webui
    restart: unless-stopped
    ports:
      - "3000:8080"          # acessível: http://VPS_IP:3000
    environment:
      OPENAI_API_BASE_URL: http://litellm:4000/v1
      OPENAI_API_KEY: ${LITELLM_MASTER_KEY}
      WEBUI_SECRET_KEY: ${WEBUI_SECRET_KEY}
      WEBUI_NAME: "Venture Studio"
      ENABLE_SIGNUP: "false"         # instância privada
      DEFAULT_MODELS: workhorse
      ENABLE_RAG_WEB_SEARCH: "false"
    volumes:
      - open_webui_data:/app/backend/data
    depends_on:
      - litellm
    networks:
      - vs_network

  # ── Ollama (embeddings locais — nomic-embed-text, grátis) ───────
  ollama:
    image: ollama/ollama:latest
    container_name: vs_ollama
    restart: unless-stopped
    ports:
      - "11434:11434"
    volumes:
      - ollama_data:/root/.ollama
    networks:
      - vs_network

  # ── Knowledge API (RAG FastAPI) ─────────────────────────────────
  knowledge_api:
    build: ./knowledge-api
    container_name: vs_knowledge_api
    restart: unless-stopped
    ports:
      - "8010:8000"
    environment:
      DATABASE_URL: postgresql://knowledge:${KNOWLEDGE_DB_PASS}@knowledge_db:5432/knowledge
      OLLAMA_URL: http://ollama:11434
      VAULT_PATH: /vault
    volumes:
      - vault_mirror:/vault:ro
    depends_on:
      knowledge_db:
        condition: service_healthy
      ollama:
        condition: service_started
    networks:
      - vs_network

  # ── Vault Sync (Dropbox → VPS, loop 15min) ─────────────────────
  vault_sync:
    build: ./knowledge-api
    container_name: vs_vault_sync
    restart: unless-stopped
    command: python3 vault_sync.py
    environment:
      DROPBOX_CREDS: /secrets/dropbox.json
      VAULT_PATH: /vault
      VAULT_DROPBOX_PATH: ${VAULT_DROPBOX_PATH}
      KNOWLEDGE_API_URL: http://knowledge_api:8000
      SYNC_INTERVAL_SECONDS: "900"
    volumes:
      - /root/.openclaw/.openclaw/workspace/secrets:/secrets:ro
      - vault_mirror:/vault
    depends_on:
      - knowledge_api
    networks:
      - vs_network

  # ── Discord Bridge (BOT 01 + BOT 02 via slash commands) ─────────
  discord_bridge:
    build: ./discord-bridge
    container_name: vs_discord_bridge
    restart: unless-stopped
    environment:
      DISCORD_TOKEN: ${DISCORD_TOKEN}
      DISCORD_GUILD_ID: ${DISCORD_GUILD_ID}
      LITELLM_URL: http://litellm:4000
      LITELLM_KEY: ${LITELLM_MASTER_KEY}
      DEFAULT_MODEL: workhorse
    depends_on:
      - litellm
    networks:
      - vs_network

  # ── Automation Runner (BOT 05 — jobs agendados) ─────────────────
  automation_runner:
    build: ./automation-runner
    container_name: vs_automation_runner
    restart: unless-stopped
    environment:
      REDIS_URL: redis://redis:6379/1
      LITELLM_URL: http://litellm:4000
      LITELLM_KEY: ${LITELLM_MASTER_KEY}
      KNOWLEDGE_API_URL: http://knowledge_api:8000
    depends_on:
      - redis
      - litellm
    networks:
      - vs_network

networks:
  vs_network:
    name: venture_studio_network
    driver: bridge

volumes:
  knowledge_db_data:
  redis_data:
  open_webui_data:
  ollama_data:
  vault_mirror:
```

- [ ] **Step 3: Commit**

```bash
git add docker-compose.yml litellm/config.yaml
git commit -m "feat: docker-compose + LiteLLM config (5 model aliases)"
git push
```

---

### Task 4: Deploy Phase 0 no VPS

- [ ] **Step 1: Pull no VPS**

```bash
cd /opt/venture-studio && git pull
```

- [ ] **Step 2: Verificar .env preenchido**

```bash
cat /opt/venture-studio/.env | grep -v "^#" | grep -v "^$"
```

Esperado: todas as variáveis com valores reais (não `your_xxx_here`).

- [ ] **Step 3: Tornar init script executável no VPS**

```bash
chmod +x /opt/venture-studio/knowledge-api/init-create-litellm-db.sh
```

- [ ] **Step 4: Subir serviços de Phase 0**

```bash
cd /opt/venture-studio
docker compose up -d knowledge_db redis litellm open_webui
```

Aguardar ~30 segundos para init do PostgreSQL.

- [ ] **Step 5: Verificar serviços activos**

```bash
docker ps --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}" | grep vs_
```

Esperado:
```
vs_knowledge_db    Up ... (healthy)   0.0.0.0:5433->5432/tcp
vs_redis           Up ... (healthy)   0.0.0.0:6380->6379/tcp
vs_litellm         Up ...             0.0.0.0:4000->4000/tcp
vs_open_webui      Up ...             0.0.0.0:3000->8080/tcp
```

- [ ] **Step 6: Testar LiteLLM**

```bash
source /opt/venture-studio/.env
curl -s http://localhost:4000/health | python3 -m json.tool
```

Esperado: `{"status": "healthy", ...}`

- [ ] **Step 7: Testar rota workhorse**

```bash
source /opt/venture-studio/.env
curl -s -X POST http://localhost:4000/v1/chat/completions \
  -H "Authorization: Bearer ${LITELLM_MASTER_KEY}" \
  -H "Content-Type: application/json" \
  -d '{"model": "workhorse", "messages": [{"role": "user", "content": "Responde em PT-BR: sistema operacional."}], "max_tokens": 30}' \
  | python3 -m json.tool | grep content
```

Esperado: linha com conteúdo de resposta em PT-BR.

- [ ] **Step 8: Abrir firewall para Open WebUI**

```bash
ufw allow 3000/tcp comment "Open WebUI Venture Studio"
ufw status
```

- [ ] **Step 9: Testar Open WebUI no browser**

Abrir: `http://37.60.236.227:3000`

Esperado: Ecrã de login "Venture Studio". Criar conta admin (primeira conta = admin automático).

---

## Phase 1 — BOT 01 Personal Assistant

### Task 5: Configurar BOT 01 no Open WebUI

Sem código Python — só configuração via interface.

- [ ] **Step 1: Aceder a Admin Panel**

`http://37.60.236.227:3000` → Login → `Admin Panel` (ícone canto inferior esquerdo)

- [ ] **Step 2: Verificar modelos disponíveis**

`Admin Panel → Settings → Models`

Deve aparecer: `cheap`, `workhorse`, `coder`, `review`, `nuclear`.

Se não aparecer: ir a `Settings → Connections` e verificar que `OPENAI_API_BASE_URL` é `http://litellm:4000/v1`.

- [ ] **Step 3: Criar preset "BOT 01" em Workspace → Models → + Create a model**

Nome: `BOT 01 — Assistente Pessoal`
Model ID: `bot01`
Base Model: `workhorse`

System Prompt (copiar exactamente):

```
Você é o assistente pessoal sénior e parceiro estratégico do Hélio Gil, empreendedor português construindo um Venture Building OS com IA.

CONTEXTO:
- Primeiro produto: SharpAnalysis (SaaS análise esportiva, live em sharpanalysis.cloud, Sprint 24 concluído)
- Orçamento apertado: R$500/mês total até gerar caixa
- Infra: VPS Contabo + OpenClaw + n8n + FastAPI + PostgreSQL + Docker
- Objetivo: "fábrica de negócios" — lançar múltiplos produtos com infra compartilhada

SUAS FUNÇÕES (tudo excepto código pesado):
• Pesquisa — modelos, preços, benchmarks, docs, mercado, concorrentes
• Planeamento — arquitectura funcional, specs em linguagem natural, roadmaps
• Síntese — resumos de documentos, consolidação de ideias, decisões
• Escrita — copy, emails, planos, briefings, relatórios
• Orquestração — gerar prompts para o Coder, tickets, issues, briefings técnicos
• Decisão de stack — análise custo-benefício, comparativos

NÃO FAÇAS:
• Código de produção (isso é BOT 02 / Coder — informe e crie o briefing)
• Debug pesado de código
• Deploy ou config de infra
• Respostas longas sem ser pedido

COMPORTAMENTO:
1. Respostas CURTAS por padrão — extensão só se pedida explicitamente
2. Português do Brasil (pt-BR), excepto termos técnicos
3. Bullets > parágrafos longos
4. Termine sempre com "→ Próximo passo:" + acção concreta
5. Se a tarefa é implementação → diga "Vou preparar o briefing para o Coder:" e faça-o

CONSCIÊNCIA DE CUSTO:
• Você roda em 'workhorse' (Qwen3 235B — barato e potente)
• Seja conciso — tokens custam dinheiro
• NUNCA sugira usar Claude Opus para tarefas rotineiras
```

Parameters:
- Temperature: `0.7`
- Max Tokens: `1000`

- [ ] **Step 4: Testar BOT 01**

Nova conversa → seleccionar "BOT 01 — Assistente Pessoal".

Mensagem de teste:
```
Qual modelo LLM é mais custo-eficiente para orquestrador de agentes em Abril 2026? 
Top 3, bullets, preços.
```

Esperado: Resposta em PT-BR, concisa, bullets, "→ Próximo passo:" ao final.

- [ ] **Step 5: Criar preset "BOT 02 — Coder"**

Nome: `BOT 02 — Coder`
Model ID: `bot02`
Base Model: `coder`
Temperature: `0.3` (mais determinístico para código)
Max Tokens: `4000`

System Prompt:
```
Você é um desenvolvedor sénior do Venture Studio.
Stack prioritária: Python 3.12, FastAPI, Pydantic v2, PostgreSQL 16, Docker, pytest.

REGRAS:
1. Plano em bullets ANTES de qualquer código
2. Código completo — sem "..." nem "rest of code here"
3. Teste básico incluído com cada implementação
4. Diffs pequenos — uma coisa de cada vez
5. Comentários explicam PORQUÊ, não o quê

NEGATIVAS:
• Nunca adicione features não pedidas
• Nunca use placeholders — código real ou nenhum código
• Nunca adicione error handling especulativo
```

---

### Task 6: Discord Bridge

**Files:**
- Create: `discord-bridge/requirements.txt`
- Create: `discord-bridge/bot.py`
- Create: `discord-bridge/Dockerfile`

- [ ] **Step 1: Criar aplicação Discord**

1. Aceder a https://discord.com/developers/applications
2. `New Application` → Nome: "Venture Studio Bot"
3. `Bot` → `Add Bot` → `Reset Token` → copiar para `.env` → `DISCORD_TOKEN`
4. `Bot` → activar:
   - `Message Content Intent` ✅
   - `Server Members Intent` ✅
5. `OAuth2 → URL Generator`:
   - Scopes: `bot`, `applications.commands`
   - Permissions: `Send Messages`, `Use Slash Commands`, `Read Message History`
6. Copiar URL gerada → abrir no browser → adicionar bot ao servidor
7. Copiar ID do servidor: (modo dev on → right-click servidor → Copy Server ID) → `DISCORD_GUILD_ID`

- [ ] **Step 2: Criar `discord-bridge/requirements.txt`**

```
discord.py==2.3.2
httpx==0.27.0
```

- [ ] **Step 3: Criar `discord-bridge/bot.py`**

```python
"""
discord-bridge/bot.py
Bot Discord para acesso ao Venture Studio.
Slash commands: /ask (BOT 01), /code (BOT 02), /status
"""
import discord
from discord import app_commands
import httpx
import os

LITELLM_URL = os.environ["LITELLM_URL"]
LITELLM_KEY = os.environ["LITELLM_KEY"]
DEFAULT_MODEL = os.environ.get("DEFAULT_MODEL", "workhorse")
CODER_MODEL = "coder"
GUILD_ID = int(os.environ["DISCORD_GUILD_ID"])

BOT01_SYSTEM = """Você é o assistente pessoal do Hélio Gil, Venture Studio.
Respostas concisas em PT-BR. Bullets > parágrafos. Termine com '→ Próximo passo:'."""

BOT02_SYSTEM = """Você é um desenvolvedor sénior. Para a tarefa recebida:
1. Plano em bullets (o que criar/modificar)
2. Código completo (sem placeholders)
3. Teste básico
Seja directo. Código > explicação."""

intents = discord.Intents.default()
intents.message_content = True
client = discord.Client(intents=intents)
tree = app_commands.CommandTree(client)


async def call_llm(model: str, system: str, user_msg: str, max_tokens: int = 1000) -> str:
    async with httpx.AsyncClient(timeout=120) as http:
        resp = await http.post(
            f"{LITELLM_URL}/v1/chat/completions",
            headers={"Authorization": f"Bearer {LITELLM_KEY}"},
            json={
                "model": model,
                "messages": [
                    {"role": "system", "content": system},
                    {"role": "user", "content": user_msg},
                ],
                "max_tokens": max_tokens,
            },
        )
        data = resp.json()

    if "choices" in data:
        return data["choices"][0]["message"]["content"]
    err = data.get("error", {})
    return f"⚠️ Erro: {err.get('message', str(data))}"


def truncate(text: str, limit: int = 1900) -> str:
    if len(text) <= limit:
        return text
    return text[:limit] + "\n*(truncado — abrir Open WebUI para resposta completa)*"


@tree.command(
    name="ask",
    description="Perguntar ao BOT 01 (pesquisa, planeamento, síntese)",
    guild=discord.Object(id=GUILD_ID),
)
@app_commands.describe(pergunta="Sua pergunta ou tarefa")
async def cmd_ask(interaction: discord.Interaction, pergunta: str):
    await interaction.response.defer(thinking=True)
    resposta = await call_llm(DEFAULT_MODEL, BOT01_SYSTEM, pergunta)
    await interaction.followup.send(f"**BOT 01:**\n{truncate(resposta)}")


@tree.command(
    name="code",
    description="Delegar implementação ao BOT 02 (Coder)",
    guild=discord.Object(id=GUILD_ID),
)
@app_commands.describe(tarefa="Descreva o que precisa ser implementado")
async def cmd_code(interaction: discord.Interaction, tarefa: str):
    await interaction.response.defer(thinking=True)
    resposta = await call_llm(CODER_MODEL, BOT02_SYSTEM, tarefa, max_tokens=2000)
    await interaction.followup.send(f"**BOT 02 (Coder):**\n{truncate(resposta)}")


@tree.command(
    name="status",
    description="Estado do Venture Studio",
    guild=discord.Object(id=GUILD_ID),
)
async def cmd_status(interaction: discord.Interaction):
    await interaction.response.defer(thinking=True)
    async with httpx.AsyncClient(timeout=10) as http:
        try:
            resp = await http.get(
                f"{LITELLM_URL}/health/liveliness",
                headers={"Authorization": f"Bearer {LITELLM_KEY}"},
            )
            health = "✅ LiteLLM online" if resp.status_code == 200 else f"⚠️ {resp.status_code}"
        except Exception as e:
            health = f"❌ LiteLLM offline: {e}"

    msg = (
        f"**Venture Studio — Status**\n"
        f"{health}\n"
        f"Modelos: `cheap` | `workhorse` | `coder` | `review` | `nuclear`\n"
        f"Open WebUI: http://37.60.236.227:3000\n"
    )
    await interaction.followup.send(msg)


@client.event
async def on_ready():
    await tree.sync(guild=discord.Object(id=GUILD_ID))
    print(f"Discord Bridge online: {client.user} | Guild: {GUILD_ID}")


client.run(os.environ["DISCORD_TOKEN"])
```

- [ ] **Step 4: Criar `discord-bridge/Dockerfile`**

```dockerfile
FROM python:3.12-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY bot.py .
CMD ["python3", "bot.py"]
```

- [ ] **Step 5: Commit e deploy**

```bash
git add discord-bridge/
git commit -m "feat: Discord bridge (BOT 01 /ask, BOT 02 /code, /status)"
git push
```

```bash
# No VPS
cd /opt/venture-studio && git pull
docker compose up -d --build discord_bridge
docker logs vs_discord_bridge --tail 10
```

Esperado: `Discord Bridge online: VentureStudioBot#XXXX | Guild: ...`

- [ ] **Step 6: Testar no Discord**

```
/ask Qual é o custo mensal estimado de usar Qwen3 235B como assistente diário?
```

Esperado: Resposta em PT-BR com estimativa de custo.

```
/status
```

Esperado: Status com LiteLLM online e lista de modelos.

---

## Phase 2 — Knowledge Engine

### Task 7: Criar knowledge-api (FastAPI RAG)

**Files:**
- Create: `knowledge-api/requirements.txt`
- Create: `knowledge-api/main.py`
- Create: `knowledge-api/Dockerfile`

- [ ] **Step 1: Criar `knowledge-api/requirements.txt`**

```
fastapi==0.115.0
uvicorn[standard]==0.30.0
psycopg2-binary==2.9.9
httpx==0.27.0
pydantic==2.7.0
dropbox==12.0.2
```

- [ ] **Step 2: Criar `knowledge-api/main.py`**

```python
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
            f"{OLLAMA_URL}/api/embeddings",
            json={"model": EMBED_MODEL, "prompt": text[:8000]},
        )
        resp.raise_for_status()
        return resp.json()["embedding"]


class SearchRequest(BaseModel):
    query: str
    limit: int = 5
    score_threshold: float = 0.50


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

    embedding = await embed(req.query)

    conn = get_conn()
    try:
        cur = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
        cur.execute(
            """
            SELECT source_path, title, content,
                   1 - (embedding <=> %s::vector) AS score
            FROM documents
            WHERE embedding IS NOT NULL
            ORDER BY embedding <=> %s::vector
            LIMIT %s
            """,
            (json.dumps(embedding), json.dumps(embedding), req.limit * 2),
        )
        rows = cur.fetchall()
    finally:
        conn.close()

    results = []
    for row in rows:
        score = float(row["score"])
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
            SET title     = EXCLUDED.title,
                content   = EXCLUDED.content,
                embedding = EXCLUDED.embedding,
                metadata  = EXCLUDED.metadata,
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
```

- [ ] **Step 3: Criar `knowledge-api/Dockerfile`**

```dockerfile
FROM python:3.12-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
```

- [ ] **Step 4: Commit**

```bash
git add knowledge-api/main.py knowledge-api/requirements.txt knowledge-api/Dockerfile
git commit -m "feat: knowledge API (FastAPI RAG com pgvector + Ollama)"
```

---

### Task 8: vault_sync.py — Dropbox → VPS + auto-indexação

**Files:**
- Create: `knowledge-api/vault_sync.py`

- [ ] **Step 1: Criar `knowledge-api/vault_sync.py`**

```python
"""
knowledge-api/vault_sync.py
Sincroniza vault Obsidian do Dropbox para /vault no VPS.
Após sync, indexa ficheiros novos/modificados via knowledge-api.
Loop: a cada SYNC_INTERVAL_SECONDS (default: 900 = 15 min).
"""
import dropbox
import dropbox.files
import os
import json
import time
import logging
import httpx
from pathlib import Path

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
)
logger = logging.getLogger(__name__)

DROPBOX_CREDS = os.environ.get("DROPBOX_CREDS", "/secrets/dropbox.json")
VAULT_PATH = Path(os.environ.get("VAULT_PATH", "/vault"))
VAULT_DROPBOX_PATH = os.environ.get("VAULT_DROPBOX_PATH", "/Obsidian")
KNOWLEDGE_API_URL = os.environ.get("KNOWLEDGE_API_URL", "http://vs_knowledge_api:8000")
SYNC_INTERVAL = int(os.environ.get("SYNC_INTERVAL_SECONDS", "900"))


def get_dbx() -> dropbox.Dropbox:
    with open(DROPBOX_CREDS) as f:
        creds = json.load(f)
    return dropbox.Dropbox(
        oauth2_refresh_token=creds["refresh_token"],
        app_key=creds["app_key"],
        app_secret=creds["app_secret"],
    )


def sync_vault(dbx: dropbox.Dropbox) -> list:
    """Sincroniza .md do Dropbox para VAULT_PATH. Retorna lista de paths actualizados."""
    VAULT_PATH.mkdir(parents=True, exist_ok=True)
    updated = []

    try:
        result = dbx.files_list_folder(VAULT_DROPBOX_PATH, recursive=True)
    except dropbox.exceptions.ApiError as e:
        logger.error(f"Dropbox API error: {e}")
        return []

    while True:
        for entry in result.entries:
            if not isinstance(entry, dropbox.files.FileMetadata):
                continue
            if not entry.name.endswith(".md"):
                continue

            rel_path = entry.path_lower.replace(
                VAULT_DROPBOX_PATH.lower() + "/", "", 1
            )
            local_path = VAULT_PATH / rel_path
            local_path.parent.mkdir(parents=True, exist_ok=True)

            if local_path.exists():
                local_mtime = local_path.stat().st_mtime
                remote_mtime = entry.server_modified.timestamp()
                if local_mtime >= remote_mtime:
                    continue  # não modificado

            dbx.files_download_to_file(str(local_path), entry.path_lower)
            updated.append(str(local_path))
            logger.info(f"Synced: {entry.path_lower}")

        if not result.has_more:
            break
        result = dbx.files_list_folder_continue(result.cursor)

    return updated


def index_files(file_paths: list) -> None:
    """Envia ficheiros para knowledge-api indexar."""
    for path in file_paths:
        try:
            content = Path(path).read_text(encoding="utf-8", errors="replace")
            if len(content.strip()) < 50:
                continue  # ignora notas quase vazias

            title = Path(path).stem
            source_path = "vault:/" + path.replace(str(VAULT_PATH) + "/", "")

            with httpx.Client(timeout=60) as http:
                resp = http.post(
                    f"{KNOWLEDGE_API_URL}/index",
                    json={
                        "source_path": source_path,
                        "title": title,
                        "content": content,
                        "metadata": {"file_path": path},
                    },
                )
                if resp.status_code == 200:
                    logger.info(f"Indexed: {title}")
                else:
                    logger.warning(f"Index failed {path}: {resp.text[:200]}")
        except Exception as e:
            logger.error(f"Error indexing {path}: {e}")


def main():
    logger.info(
        f"Vault sync started. Dropbox: {VAULT_DROPBOX_PATH} → Local: {VAULT_PATH}"
    )
    logger.info(f"Sync interval: {SYNC_INTERVAL}s ({SYNC_INTERVAL // 60}min)")

    while True:
        try:
            dbx = get_dbx()
            updated = sync_vault(dbx)
            logger.info(f"Sync complete: {len(updated)} files updated")
            if updated:
                index_files(updated)
                logger.info(f"Indexed: {len(updated)} files")
        except Exception as e:
            logger.error(f"Sync cycle error: {e}", exc_info=True)
        time.sleep(SYNC_INTERVAL)


if __name__ == "__main__":
    main()
```

- [ ] **Step 2: Commit**

```bash
git add knowledge-api/vault_sync.py
git commit -m "feat: vault sync (Dropbox → VPS + auto-indexação)"
git push
```

---

### Task 9: Deploy Knowledge Engine

- [ ] **Step 1: Pull e build no VPS**

```bash
cd /opt/venture-studio && git pull
docker compose up -d --build ollama knowledge_api
```

- [ ] **Step 2: Pull do modelo de embeddings**

```bash
docker exec vs_ollama ollama pull nomic-embed-text
```

Aguardar download (~274MB). Verificar:

```bash
docker exec vs_ollama ollama list
```

Esperado: `nomic-embed-text` na lista.

- [ ] **Step 3: Testar embedding**

```bash
curl -s http://localhost:11434/api/embeddings \
  -d '{"model": "nomic-embed-text", "prompt": "teste"}' \
  | python3 -c "import sys,json; d=json.load(sys.stdin); print(f'Dims: {len(d[\"embedding\"])}')"
```

Esperado: `Dims: 768`

- [ ] **Step 4: Testar knowledge-api**

```bash
curl http://localhost:8010/health
```

Esperado: `{"status":"ok","embed_model":"nomic-embed-text"}`

- [ ] **Step 5: Testar indexação manual**

```bash
curl -s -X POST http://localhost:8010/index \
  -H "Content-Type: application/json" \
  -d '{
    "source_path": "vault:/teste/venture-studio.md",
    "title": "Venture Studio Overview",
    "content": "O Venture Studio é uma infraestrutura de venture building com IA. SharpAnalysis é o primeiro produto, um SaaS de análise esportiva."
  }' | python3 -m json.tool
```

Esperado: `{"indexed": "vault:/teste/venture-studio.md", "status": "ok"}`

- [ ] **Step 6: Testar busca semântica**

```bash
curl -s -X POST http://localhost:8010/search \
  -H "Content-Type: application/json" \
  -d '{"query": "primeiro produto SaaS esportivo", "limit": 3}' | python3 -m json.tool
```

Esperado: resultado com `venture-studio.md`, score > 0.6.

- [ ] **Step 7: Verificar path do vault no Dropbox**

```bash
cd /root/.openclaw/.openclaw/workspace
python3 scripts/dropbox_helper.py list --folder /
```

Verificar qual pasta contém o vault Obsidian. Se não for `/Obsidian`, actualizar `.env`:

```bash
nano /opt/venture-studio/.env
# Alterar VAULT_DROPBOX_PATH=/NomeDaPastaReal
```

- [ ] **Step 8: Subir vault_sync**

```bash
cd /opt/venture-studio
docker compose up -d vault_sync
docker logs vs_vault_sync -f --tail 20
```

Esperado: logs de ficheiros a sincronizar do Dropbox → indexados.

---

## Phase 3 — BOT 02 Coder (extended)

BOT 02 já está funcional via Discord `/code` e Open WebUI preset "BOT 02 — Coder" (criados na Task 6/5).

### Task 10: Integrar RAG no fluxo do BOT 01

Actualmente o BOT 01 não usa a knowledge-api automaticamente. Para injectar contexto do vault:

- [ ] **Step 1: Criar Open WebUI Pipe function**

`Admin Panel → Functions → + Create Function`

Nome: `Knowledge RAG Pipe`
Tipo: `Pipe`

```python
"""
Open WebUI Pipe: injjecta contexto do knowledge base no prompt do BOT 01.
Chama knowledge-api antes de enviar para o LLM.
"""
from pydantic import BaseModel
import httpx
import os

KNOWLEDGE_API_URL = os.environ.get("KNOWLEDGE_API_URL", "http://vs_knowledge_api:8000")


class Pipe:
    class Valves(BaseModel):
        knowledge_api_url: str = KNOWLEDGE_API_URL
        max_context_results: int = 3

    def __init__(self):
        self.valves = self.Valves()

    async def pipe(self, body: dict) -> dict:
        """Intercepta request, busca contexto relevante, injjecta no system prompt."""
        messages = body.get("messages", [])
        if not messages:
            return body

        # Última mensagem do utilizador = query de busca
        last_user_msg = next(
            (m["content"] for m in reversed(messages) if m["role"] == "user"),
            "",
        )

        if not last_user_msg:
            return body

        try:
            async with httpx.AsyncClient(timeout=10) as http:
                resp = await http.post(
                    f"{self.valves.knowledge_api_url}/search",
                    json={
                        "query": last_user_msg[:500],
                        "limit": self.valves.max_context_results,
                    },
                )
                results = resp.json() if resp.status_code == 200 else []
        except Exception:
            return body  # falha silenciosa — não bloquear resposta

        if not results:
            return body

        # Montar contexto a injectar
        context_parts = []
        for r in results:
            if r.get("score", 0) >= 0.5:
                context_parts.append(
                    f"[Fonte: {r['title'] or r['source_path']}]\n{r['content_snippet']}"
                )

        if not context_parts:
            return body

        context_block = "\n\n---\n".join(context_parts)
        rag_injection = (
            f"\n\n[CONTEXTO DO KNOWLEDGE BASE — usar como referência se relevante:]\n{context_block}\n"
        )

        # Injectar no system prompt (ou criar um se não existir)
        if messages[0]["role"] == "system":
            messages[0]["content"] += rag_injection
        else:
            messages.insert(0, {"role": "system", "content": rag_injection})

        body["messages"] = messages
        return body
```

- [ ] **Step 2: Activar Pipe no modelo BOT 01**

`Workspace → Models → BOT 01 — Assistente Pessoal → Edit → Pipe Functions → Activar Knowledge RAG Pipe`

- [ ] **Step 3: Testar RAG integrado**

Nova conversa com BOT 01. Mensagem sobre algo que está no vault:

```
O que sabes sobre o SharpAnalysis e as suas funcionalidades?
```

Esperado: Resposta com informação específica do vault (não apenas conhecimento genérico do modelo).

---

## Phase 4 — Automation Runner (BOT 05)

### Task 11: Setup básico de jobs agendados

**Files:**
- Create: `automation-runner/requirements.txt`
- Create: `automation-runner/runner.py`
- Create: `automation-runner/Dockerfile`

- [ ] **Step 1: Criar `automation-runner/requirements.txt`**

```
dramatiq[redis]==1.17.0
apscheduler==3.10.4
httpx==0.27.0
redis==5.0.4
```

- [ ] **Step 2: Criar `automation-runner/runner.py`**

```python
"""
automation-runner/runner.py
BOT 05 — Automation Runner.
Jobs agendados: health check horário, relatório de custo diário.
Extensível: adicionar novos @dramatiq.actor + scheduler.add_job.
"""
import dramatiq
from dramatiq.brokers.redis import RedisBroker
from apscheduler.schedulers.blocking import BlockingScheduler
import httpx
import os
import logging

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
)
logger = logging.getLogger(__name__)

REDIS_URL = os.environ.get("REDIS_URL", "redis://vs_redis:6379/1")
LITELLM_URL = os.environ.get("LITELLM_URL", "http://vs_litellm:4000")
LITELLM_KEY = os.environ.get("LITELLM_KEY", "")
KNOWLEDGE_API_URL = os.environ.get("KNOWLEDGE_API_URL", "http://vs_knowledge_api:8000")

broker = RedisBroker(url=REDIS_URL)
dramatiq.set_broker(broker)


@dramatiq.actor
def health_check():
    """Verifica saúde dos serviços core. Loga resultado."""
    services = {
        "litellm": (f"{LITELLM_URL}/health/liveliness", {"Authorization": f"Bearer {LITELLM_KEY}"}),
        "knowledge_api": (f"{KNOWLEDGE_API_URL}/health", {}),
    }
    with httpx.Client(timeout=10) as http:
        for name, (url, headers) in services.items():
            try:
                resp = http.get(url, headers=headers)
                status = "OK" if resp.status_code == 200 else f"HTTP {resp.status_code}"
            except Exception as e:
                status = f"ERROR: {e}"
            logger.info(f"Health {name}: {status}")


@dramatiq.actor
def daily_cost_report():
    """Relatório diário de custo de tokens via LiteLLM spend logs."""
    with httpx.Client(timeout=15) as http:
        try:
            resp = http.get(
                f"{LITELLM_URL}/spend/logs",
                headers={"Authorization": f"Bearer {LITELLM_KEY}"},
            )
            data = resp.json()
            entries = data.get("data", [])
            total = sum(float(e.get("spend", 0)) for e in entries)
            logger.info(f"Daily spend: US${total:.4f} ({len(entries)} requests)")
        except Exception as e:
            logger.error(f"Cost report error: {e}")


def main():
    scheduler = BlockingScheduler(timezone="UTC")

    # Health check a cada hora
    scheduler.add_job(health_check.send, "interval", hours=1, id="health_check")

    # Relatório de custo todos os dias às 08:00 UTC
    scheduler.add_job(
        daily_cost_report.send, "cron",
        hour=8, minute=0,
        id="daily_cost_report",
    )

    logger.info("BOT 05 — Automation Runner iniciado")
    scheduler.start()


if __name__ == "__main__":
    main()
```

- [ ] **Step 3: Criar `automation-runner/Dockerfile`**

```dockerfile
FROM python:3.12-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY runner.py .
CMD ["python3", "runner.py"]
```

- [ ] **Step 4: Commit e deploy**

```bash
git add automation-runner/
git commit -m "feat: BOT 05 Automation Runner (Dramatiq + APScheduler)"
git push

# VPS
cd /opt/venture-studio && git pull
docker compose up -d --build automation_runner
docker logs vs_automation_runner --tail 10
```

Esperado: `BOT 05 — Automation Runner iniciado` nos logs.

---

## Verificação Final — Sistema Completo

- [ ] **Step 1: Todos os containers activos**

```bash
docker ps --format "table {{.Names}}\t{{.Status}}" | grep vs_
```

Esperado (todos Up):
```
vs_knowledge_db       Up ... (healthy)
vs_redis              Up ... (healthy)
vs_litellm            Up ...
vs_open_webui         Up ...
vs_ollama             Up ...
vs_knowledge_api      Up ...
vs_vault_sync         Up ...
vs_discord_bridge     Up ...
vs_automation_runner  Up ...
```

- [ ] **Step 2: Open WebUI acessível e BOT 01 funciona**

`http://37.60.236.227:3000` → conversa com "BOT 01 — Assistente Pessoal" → resposta em PT-BR.

- [ ] **Step 3: Discord responde**

No servidor Discord: `/ask Qual é o plano do Venture Studio?` → resposta em <30 segundos.

- [ ] **Step 4: Knowledge base tem documentos**

```bash
curl -s -X POST http://localhost:8010/search \
  -H "Content-Type: application/json" \
  -d '{"query": "venture building", "limit": 3}' | python3 -m json.tool
```

Esperado: resultados com conteúdo real do vault.

- [ ] **Step 5: LiteLLM roteia correctamente**

```bash
source /opt/venture-studio/.env
curl -s http://localhost:4000/model/info \
  -H "Authorization: Bearer ${LITELLM_MASTER_KEY}" | python3 -m json.tool | grep model_name
```

Esperado: todos os 5 aliases listados.

---

## Notas de Segurança

- **Porta 4000 (LiteLLM):** NÃO abrir ao exterior — acesso apenas interno via Docker network.
- **Porta 3000 (Open WebUI):** Exposta ao exterior — `ENABLE_SIGNUP: "false"` protege de acessos não autorizados.
- **Secrets:** Nunca commitar `.env` — está em `.gitignore`. Copiar manualmente para o VPS.
- **Discord Token:** Mantê-lo apenas no `.env` do VPS, nunca no código.

## O Que Fica Fora Deste Plano (próximas iterações)

| Item | Quando adicionar |
|------|-----------------|
| Nginx reverse proxy (HTTPS para Open WebUI) | Quando houver utilizadores externos |
| BOT 03 Knowledge Manager autónomo (curadoria inteligente do vault) | Após vault indexado e estável |
| SharpAnalysis Pod (marketing, SAC, analytics bots) | Após infra-mãe validada com 2+ semanas de uso |
| Mac Mini com Proxmox + VMs | Após receita ou quando VPS for gargalo |
| WhatsApp bridge (Twilio/Evolution API) | Quando orçamento permitir (~R$50-100/mês extra) |
| Imagem/vídeo para ads (Replicate, fal.ai) | SharpAnalysis marketing pod fase 2 |
| Multi-tenant / pods isolados por produto | Após 2º produto activo |
| LiteLLM → serviço dedicado de custo por produto | Quando houver 3+ produtos gerando receita |
