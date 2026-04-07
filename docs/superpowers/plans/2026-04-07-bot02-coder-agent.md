# BOT 02 — Coder Agent (Async Batch) — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Pipeline async Claude Code → Jarvis → Coder → devolucoes → Discord notify. Claude Code deposita lote de tarefas no final de cada sessão; BOT 02 processa durante o dia; próxima sessão Claude Code lê resultados e continua.

**Architecture:** Novo serviço Docker `task-runner` que poleia `solicitacoes/` no vault a cada 30min, processa com modelo Coder via LiteLLM, escreve em `devolucoes/`, faz upload directo para Dropbox, notifica Discord.

**Tech Stack:** Python 3.12, dropbox SDK, httpx, APScheduler, docker-compose, Markdown frontmatter (PyYAML)

---

## Folder Structure (Dropbox/Vault)

```
/Aplicativos/remotely-save/Hélio Gil/
  venture-studio/
    tarefas/
      solicitacoes/     ← Claude Code escreve aqui (local Dropbox)
      devolucoes/       ← task-runner escreve + upload Dropbox
      arquivo/          ← tarefas processadas movidas aqui (histórico)
```

## Task File Format

```markdown
---
id: task-001
sessao: 2026-04-07
prioridade: alta
modelo: Coder
max_tokens: 2000
contexto:
  - knowledge-api/main.py
  - docker-compose.yml
status: pendente
---

## Tarefa
Descrição clara e atómica do que precisa ser feito.

## Critérios de aceitação
- [ ] Critério 1
- [ ] Critério 2

## Contexto adicional
Qualquer informação relevante que o Coder precisa saber.
```

## Result File Format (devolucoes/)

```markdown
---
id: task-001
status: concluido
modelo_usado: Coder
tokens_usados: 1847
sessao_origem: 2026-04-07
entregue_em: 2026-04-07T14:32:00Z
---

## Resultado

[código ou entrega do Coder]

## Notas do Coder
[observações, limitações, sugestões]
```

---

## File Structure

- Create: `task-runner/runner.py` — serviço principal
- Create: `task-runner/requirements.txt`
- Create: `task-runner/Dockerfile`
- Modify: `docker-compose.yml` — adicionar serviço task_runner
- Modify: `discord-bridge/bot.py` — endpoint interno para receber notificação do task-runner

---

## Task 1: Estrutura de pastas no Dropbox

**Files:**
- No code — acção manual + verificação

- [ ] **Step 1: Criar pastas no Dropbox local**

Criar manualmente no Dropbox (Windows Explorer ou Finder):
```
Dropbox/Aplicativos/remotely-save/Hélio Gil/venture-studio/tarefas/solicitacoes/
Dropbox/Aplicativos/remotely-save/Hélio Gil/venture-studio/tarefas/devolucoes/
Dropbox/Aplicativos/remotely-save/Hélio Gil/venture-studio/tarefas/arquivo/
```

- [ ] **Step 2: Criar ficheiro .gitkeep em cada pasta**

Criar ficheiro vazio `.gitkeep` em cada pasta para o Dropbox reconhecer.

- [ ] **Step 3: Verificar sync no VPS**

```bash
ssh root@37.60.236.227
ls /vault/venture-studio/tarefas/
# Deve mostrar: solicitacoes/ devolucoes/ arquivo/
```

Expected: pastas visíveis após próximo vault_sync (max 15min)

---

## Task 2: task-runner/requirements.txt e Dockerfile

**Files:**
- Create: `task-runner/requirements.txt`
- Create: `task-runner/Dockerfile`

- [ ] **Step 1: Criar requirements.txt**

```
httpx==0.27.0
apscheduler==3.10.4
dropbox==12.0.2
PyYAML==6.0.2
```

- [ ] **Step 2: Criar Dockerfile**

```dockerfile
FROM python:3.12-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY runner.py .
CMD ["python3", "runner.py"]
```

- [ ] **Step 3: Commit**

```bash
git add task-runner/
git commit -m "feat: task-runner Dockerfile + requirements"
```

---

## Task 3: task-runner/runner.py — core logic

**Files:**
- Create: `task-runner/runner.py`

- [ ] **Step 1: Estrutura base com APScheduler**

```python
"""
task-runner/runner.py
BOT 02 — Coder Agent async batch processor.
Poll solicitacoes/ → Coder via LiteLLM → devolucoes/ → upload Dropbox → notify Discord
"""
import os
import json
import logging
import yaml
import httpx
import dropbox
from pathlib import Path
from datetime import datetime, timezone
from apscheduler.schedulers.blocking import BlockingScheduler

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)

VAULT_PATH = Path(os.environ.get("VAULT_PATH", "/vault"))
TASKS_PATH = VAULT_PATH / "venture-studio" / "tarefas"
SOLICITACOES = TASKS_PATH / "solicitacoes"
DEVOLUCOES   = TASKS_PATH / "devolucoes"
ARQUIVO      = TASKS_PATH / "arquivo"

LITELLM_URL  = os.environ.get("LITELLM_URL", "http://litellm:4000")
LITELLM_KEY  = os.environ.get("LITELLM_KEY", "")
DISCORD_URL  = os.environ.get("DISCORD_WEBHOOK_URL", "")
DROPBOX_CREDS = os.environ.get("DROPBOX_CREDS", "/secrets/dropbox.json")
VAULT_DROPBOX_PATH = os.environ.get("VAULT_DROPBOX_PATH", "/Aplicativos/remotely-save/Hélio Gil")
POLL_INTERVAL = int(os.environ.get("POLL_INTERVAL_SECONDS", "1800"))  # 30min
DAILY_BUDGET_USD = float(os.environ.get("DAILY_BUDGET_USD", "1.50"))
```

- [ ] **Step 2: Funções auxiliares — parse task, get_dbx, check_budget**

```python
def parse_task(path: Path) -> dict | None:
    """Parse markdown file com frontmatter YAML."""
    try:
        content = path.read_text(encoding="utf-8")
        if content.startswith("---"):
            parts = content.split("---", 2)
            meta = yaml.safe_load(parts[1])
            body = parts[2].strip() if len(parts) > 2 else ""
        else:
            meta = {}
            body = content
        meta["_body"] = body
        meta["_path"] = str(path)
        meta["_filename"] = path.name
        return meta
    except Exception as e:
        logger.error(f"Parse error {path}: {e}")
        return None


def get_dbx() -> dropbox.Dropbox:
    with open(DROPBOX_CREDS) as f:
        creds = json.load(f)
    return dropbox.Dropbox(
        oauth2_refresh_token=creds["refresh_token"],
        app_key=creds["app_key"],
        app_secret=creds["app_secret"],
    )


def check_daily_budget() -> tuple[float, bool]:
    """Verifica spend do dia via LiteLLM. Retorna (spend, dentro_do_budget)."""
    try:
        with httpx.Client(timeout=10) as http:
            resp = http.get(
                f"{LITELLM_URL}/spend/logs",
                headers={"Authorization": f"Bearer {LITELLM_KEY}"},
            )
            entries = resp.json().get("data", [])
            total = sum(float(e.get("spend", 0)) for e in entries)
            return total, total < DAILY_BUDGET_USD
    except Exception as e:
        logger.warning(f"Budget check failed: {e} — assumindo dentro do budget")
        return 0.0, True
```

- [ ] **Step 3: Função call_coder — chama LiteLLM com modelo Coder**

```python
def call_coder(task: dict) -> tuple[str, int]:
    """Envia tarefa ao Coder. Retorna (resposta, tokens_usados)."""
    modelo = task.get("modelo", "Coder")
    max_tokens = int(task.get("max_tokens", 2000))

    system = """Você é um desenvolvedor sénior do Venture Studio.
Para cada tarefa recebida:
1. Analise os critérios de aceitação
2. Produza código completo e funcional (sem placeholders)
3. Inclua teste básico quando relevante
4. Termine com: ## Notas do Coder (observações, edge cases, limitações)
Seja directo. Código > explicação."""

    user_msg = f"{task['_body']}"
    if task.get("contexto"):
        user_msg += f"\n\nFicheiros de contexto referenciados: {task['contexto']}"

    with httpx.Client(timeout=120) as http:
        resp = http.post(
            f"{LITELLM_URL}/v1/chat/completions",
            headers={"Authorization": f"Bearer {LITELLM_KEY}"},
            json={
                "model": modelo,
                "messages": [
                    {"role": "system", "content": system},
                    {"role": "user", "content": user_msg},
                ],
                "max_tokens": max_tokens,
            },
        )
        data = resp.json()

    content = data["choices"][0]["message"]["content"]
    tokens = data.get("usage", {}).get("total_tokens", 0)
    return content, tokens
```

- [ ] **Step 4: Função process_task — orquestra tudo**

```python
def write_result(task: dict, result: str, tokens: int) -> Path:
    """Escreve ficheiro de resultado em devolucoes/."""
    DEVOLUCOES.mkdir(parents=True, exist_ok=True)
    task_id = task.get("id", Path(task["_filename"]).stem)
    out_path = DEVOLUCOES / f"{task_id}-resultado.md"

    frontmatter = {
        "id": task_id,
        "status": "concluido",
        "modelo_usado": task.get("modelo", "Coder"),
        "tokens_usados": tokens,
        "sessao_origem": task.get("sessao", ""),
        "entregue_em": datetime.now(timezone.utc).isoformat(),
    }
    content = f"---\n{yaml.dump(frontmatter, allow_unicode=True)}---\n\n## Resultado\n\n{result}\n"
    out_path.write_text(content, encoding="utf-8")
    return out_path


def upload_to_dropbox(local_path: Path) -> bool:
    """Upload ficheiro para Dropbox."""
    try:
        dbx = get_dbx()
        rel = str(local_path).replace(str(VAULT_PATH), "").replace("\\", "/")
        dropbox_path = VAULT_DROPBOX_PATH.rstrip("/") + rel
        with open(local_path, "rb") as f:
            dbx.files_upload(f.read(), dropbox_path,
                             mode=dropbox.files.WriteMode.overwrite)
        logger.info(f"Uploaded: {dropbox_path}")
        return True
    except Exception as e:
        logger.error(f"Upload failed: {e}")
        return False


def notify_discord(message: str) -> None:
    """Envia notificação via Discord webhook ou canal configurado."""
    if not DISCORD_URL:
        logger.info(f"Discord notify (no webhook): {message}")
        return
    try:
        with httpx.Client(timeout=10) as http:
            http.post(DISCORD_URL, json={"content": message})
    except Exception as e:
        logger.warning(f"Discord notify failed: {e}")


def process_task(path: Path) -> bool:
    """Processa uma tarefa. Retorna True se concluída."""
    task = parse_task(path)
    if not task:
        return False

    task_id = task.get("id", path.stem)
    logger.info(f"Processando: {task_id} | modelo={task.get('modelo','Coder')} | prioridade={task.get('prioridade','media')}")

    try:
        result, tokens = call_coder(task)
        out_path = write_result(task, result, tokens)
        upload_to_dropbox(out_path)

        # Mover para arquivo
        ARQUIVO.mkdir(parents=True, exist_ok=True)
        path.rename(ARQUIVO / path.name)

        logger.info(f"Concluido: {task_id} | {tokens} tokens")
        return True
    except Exception as e:
        logger.error(f"Erro processando {task_id}: {e}")
        return False
```

- [ ] **Step 5: Loop principal com prioridade e budget**

```python
PRIORIDADE_ORDER = {"alta": 0, "media": 1, "baixa": 2}

def run_batch():
    """Processa lote de tarefas pendentes com controlo de budget."""
    SOLICITACOES.mkdir(parents=True, exist_ok=True)
    tasks_files = sorted(
        [f for f in SOLICITACOES.glob("*.md") if not f.name.startswith(".")],
        key=lambda f: PRIORIDADE_ORDER.get(
            (parse_task(f) or {}).get("prioridade", "media"), 1
        )
    )

    if not tasks_files:
        logger.info("Nenhuma tarefa pendente.")
        return

    spend, dentro_budget = check_daily_budget()
    logger.info(f"Batch: {len(tasks_files)} tarefas | Spend hoje: ${spend:.4f} | Budget OK: {dentro_budget}")

    if not dentro_budget:
        logger.warning(f"Budget diario atingido (${spend:.2f}). Tarefas adiadas.")
        notify_discord(f"BOT 02: Budget diario atingido (${spend:.2f}). {len(tasks_files)} tarefas aguardam amanha.")
        return

    ok = err = 0
    for task_file in tasks_files:
        spend, dentro_budget = check_daily_budget()
        if not dentro_budget:
            logger.warning(f"Budget atingido a meio do batch. {len(tasks_files) - ok - err} tarefas restantes.")
            break
        if process_task(task_file):
            ok += 1
        else:
            err += 1

    total = ok + err
    if total > 0:
        msg = f"BOT 02 Coder: {ok}/{total} tarefas concluidas."
        if err:
            msg += f" {err} com erro — verificar logs."
        notify_discord(msg)
        logger.info(msg)


def main():
    scheduler = BlockingScheduler(timezone="UTC")
    scheduler.add_job(run_batch, "interval", seconds=POLL_INTERVAL, id="task_batch")
    scheduler.add_job(run_batch, "date", id="startup_run")  # run once on start
    logger.info(f"BOT 02 Task Runner iniciado | Poll: {POLL_INTERVAL}s")
    scheduler.start()


if __name__ == "__main__":
    main()
```

- [ ] **Step 6: Commit**

```bash
git add task-runner/runner.py
git commit -m "feat: task-runner runner.py — BOT 02 async batch coder agent"
```

---

## Task 4: docker-compose.yml — adicionar task_runner

**Files:**
- Modify: `docker-compose.yml`

- [ ] **Step 1: Adicionar serviço**

Adicionar após `automation_runner`:

```yaml
  # ── Task Runner (BOT 02 — Coder Agent async) ──────────────────────
  task_runner:
    build: ./task-runner
    container_name: vs_task_runner
    restart: unless-stopped
    environment:
      LITELLM_URL: http://litellm:4000
      LITELLM_KEY: ${LITELLM_MASTER_KEY}
      VAULT_PATH: /vault
      VAULT_DROPBOX_PATH: ${VAULT_DROPBOX_PATH}
      DROPBOX_CREDS: /secrets/dropbox.json
      DISCORD_WEBHOOK_URL: ${DISCORD_WEBHOOK_URL}
      POLL_INTERVAL_SECONDS: "1800"
      DAILY_BUDGET_USD: "1.50"
    volumes:
      - /root/.openclaw/.openclaw/workspace/secrets:/secrets:ro
      - vault_mirror:/vault
    depends_on:
      - litellm
      - vault_sync
    networks:
      - vs_network
```

- [ ] **Step 2: Adicionar DISCORD_WEBHOOK_URL ao .env.example**

```bash
# Discord webhook para notificações do task-runner
DISCORD_WEBHOOK_URL=https://discord.com/api/webhooks/...
```

- [ ] **Step 3: Commit**

```bash
git add docker-compose.yml .env.example
git commit -m "feat: add task_runner service to docker-compose (BOT 02)"
```

---

## Task 5: Discord Webhook para notificações do task-runner

**Files:**
- No code — acção manual

- [ ] **Step 1: Criar webhook no Discord**

No servidor Discord:
1. Clica com direito no canal → Edit Channel → Integrations → Webhooks
2. New Webhook → copia URL
3. Formato: `https://discord.com/api/webhooks/XXXXXX/YYYYYY`

- [ ] **Step 2: Adicionar ao .env no VPS**

```bash
echo "DISCORD_WEBHOOK_URL=https://discord.com/api/webhooks/..." >> /opt/venture-studio/.env
```

- [ ] **Step 3: Deploy task_runner**

```bash
cd /opt/venture-studio
docker compose build task_runner
docker compose up -d task_runner
docker logs vs_task_runner --tail 10
```

Expected: `BOT 02 Task Runner iniciado | Poll: 1800s`

---

## Task 6: Testar fluxo completo

- [ ] **Step 1: Criar tarefa de teste**

Criar ficheiro local (em Dropbox):
```
Dropbox/Aplicativos/remotely-save/Hélio Gil/venture-studio/tarefas/solicitacoes/task-teste-001.md
```

Conteúdo:
```markdown
---
id: task-teste-001
sessao: 2026-04-07
prioridade: alta
modelo: Coder
max_tokens: 500
status: pendente
---

## Tarefa
Escreve uma função Python que recebe uma lista de números e retorna a média, mínimo e máximo em formato JSON.

## Critérios de aceitação
- [ ] Função `stats(numbers: list) -> dict`
- [ ] Retorna `{"mean": x, "min": x, "max": x}`
- [ ] Teste com `[1, 2, 3, 4, 5]`
```

- [ ] **Step 2: Aguardar sync (máx 15min) ou forçar**

```bash
docker restart vs_vault_sync && sleep 30 && docker restart vs_task_runner
```

- [ ] **Step 3: Verificar resultado**

```bash
ls /vault/venture-studio/tarefas/devolucoes/
cat /vault/venture-studio/tarefas/devolucoes/task-teste-001-resultado.md
```

Expected: ficheiro com código Python + metadata YAML

- [ ] **Step 4: Verificar notificação Discord**

Deve aparecer no canal: `BOT 02 Coder: 1/1 tarefas concluidas.`

- [ ] **Step 5: Verificar Dropbox local**

```
Dropbox/Aplicativos/remotely-save/Hélio Gil/venture-studio/tarefas/devolucoes/task-teste-001-resultado.md
```

---

## Padrão de uso (Claude Code)

No final de cada sessão Claude Code, o agente deve:

1. Listar as tarefas identificadas para execução assíncrona
2. Para cada tarefa, criar ficheiro `.md` com o formato padrão em `solicitacoes/`
3. Incluir: id sequencial, prioridade, modelo, max_tokens, contexto relevante
4. Confirmar ao utilizador: "X tarefas depositadas. BOT 02 processa durante o dia. Na próxima sessão começamos por ler devolucoes/."

No início da próxima sessão:
1. Verificar `devolucoes/` — ler resultados
2. Validar cada resultado contra critérios de aceitação
3. Aplicar código/soluções ao projecto
4. Mover tarefas aprovadas para `arquivo/` (ou deixar o task-runner fazer automaticamente)
