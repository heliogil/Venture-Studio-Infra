# Venture Studio — Padrão de Implementação de Bots

> Aplicar sempre que um novo BOT for criado ou um existente for actualizado.

---

## 1. Gestão de Memória e Contexto

### 1.1 Memória Persistente (Open WebUI)
- **O quê**: factos duráveis sobre o utilizador injectados automaticamente em cada sessão
- **Como**: criar entradas via `POST /api/v1/memories/add` após criar o bot
- **Script de referência**: `scripts/owui_seed_memory.py`
- **Quando actualizar**: sempre que o utilizador partilhar nova informação estrutural (novo projecto, nova preferência, mudança de infra)

### 1.2 Vault Search (RAG)
- **O quê**: pesquisa semântica + keyword sobre as notas Obsidian do utilizador
- **Modos**: `hybrid` (padrão), `semantic`, `keyword`
- **Endpoint**: `POST http://knowledge_api:8000/search`
- **Como activar**: incluir `toolIds: ["vault_search"]` no meta do modelo
- **Script de referência**: `scripts/owui_create_tool2.py`

### 1.3 Parâmetros de Contexto (Jarvis Candango como referência)
```json
{
  "temperature": 0.7,
  "max_tokens": 1500,
  "num_ctx": 8192
}
```
- `temperature 0.7` → respostas focadas, menos verbose = menos tokens gastos
- `max_tokens 1500` → limite por resposta (evita respostas gigantes)
- `num_ctx 8192` → janela de contexto razoável para conversas longas

---

## 2. System Prompt Mínimo

Todo o bot deve incluir no system prompt:
- Língua: PT-BR
- Formato: bullets > parágrafos
- Comportamento: quando em dúvida sobre contexto do utilizador, usar `search_vault`
- Encerramento de resposta: `→ Próximo passo: [acção concreta]` quando aplicável

---

## 3. Modelos por Função

| Alias | Modelo | Usar quando |
|-------|--------|-------------|
| `Rapido` | Gemini Flash 1.5 8B | Triagem, FAQ, formatação simples |
| `Geral` | Qwen3-235B | Chat geral, pesquisa, síntese, planeamento |
| `Coder` | DeepSeek R1 | Código, debug, arquitectura técnica |
| `Revisor` | Claude Sonnet 4.6 | Revisão crítica, validação |
| `Nuclear` | Claude Opus 4.6 | Decisões fundacionais, arquitectura complexa |

**Regra de custo**: começar sempre pelo modelo mais barato que resolve o problema.

---

## 4. Checklist de Deploy (novo BOT)

```
[ ] 1. Criar modelo em Open WebUI via API (scripts/owui_recreate_model.py como base)
[ ] 2. Definir system prompt com: língua, formato, vault_search, próximo passo
[ ] 3. Configurar params: temperature=0.7, max_tokens=1500, num_ctx=8192
[ ] 4. Activar tool vault_search no meta do modelo (toolIds: ["vault_search"])
[ ] 5. Seed de memórias relevantes para o contexto do bot (scripts/owui_seed_memory.py)
[ ] 6. Testar: query simples + query que exige vault + query fora do conhecimento
[ ] 7. Actualizar landing page (docs/index.html) se o bot for público
[ ] 8. Commit + push para GitHub
```

---

## 5. Referência de Scripts

| Script | O que faz |
|--------|-----------|
| `scripts/owui_recreate_model.py` | Criar modelo com system prompt |
| `scripts/owui_create_tool2.py` | Criar tool Python no Open WebUI |
| `scripts/owui_seed_memory.py` | Seed de memórias persistentes |
| `scripts/owui_update_jarvis_params.py` | Actualizar params de um modelo |

---

## 6. Arquitectura de Custo

```
Cada sessão custa:
  + Memórias injectadas     ~200 tokens fixos (amortizado — elimina re-explicações)
  + System prompt           ~300 tokens fixos
  + Vault search (se usado) ~400 tokens variáveis
  - Max tokens por resposta 1500 (limitado)
  = Budget diário: $2 USD (LiteLLM cap)
```

Revisão de custo: ver `http://37.60.236.227:4000/ui` → Spend Logs.
