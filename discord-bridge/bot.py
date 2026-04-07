"""
discord-bridge/bot.py
Bot Discord para acesso ao Venture Studio.
- Slash commands: /ask, /code, /status
- Auto-resposta: responde a qualquer mensagem no canal BOT_CHANNEL_ID (sem @)
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
# Canal onde o bot responde a TODAS as mensagens sem precisar de @
# Deixar vazio para desactivar auto-resposta
BOT_CHANNEL_ID = int(os.environ["BOT_CHANNEL_ID"]) if os.environ.get("BOT_CHANNEL_ID") else None

BOT01_SYSTEM = """Você é o assistente pessoal do Hélio Gil, do Venture Studio.
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
    return f"Erro: {err.get('message', str(data))}"


def truncate(text: str, limit: int = 1900) -> str:
    if len(text) <= limit:
        return text
    return text[:limit] + "\n*(truncado — abrir Open WebUI para resposta completa)*"


@client.event
async def on_message(message: discord.Message):
    # Ignorar mensagens do próprio bot
    if message.author.bot:
        return
    # Auto-responder apenas no canal configurado
    if BOT_CHANNEL_ID and message.channel.id != BOT_CHANNEL_ID:
        return
    if not BOT_CHANNEL_ID:
        return  # Sem canal configurado, não auto-responde

    async with message.channel.typing():
        resposta = await call_llm(DEFAULT_MODEL, BOT01_SYSTEM, message.content)
    await message.reply(truncate(resposta), mention_author=False)


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
            health = "LiteLLM online" if resp.status_code == 200 else f"HTTP {resp.status_code}"
        except Exception as e:
            health = f"LiteLLM offline: {e}"

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
    ch = f"canal {BOT_CHANNEL_ID}" if BOT_CHANNEL_ID else "auto-resposta desactivada"
    print(f"Discord Bridge online: {client.user} | Guild: {GUILD_ID} | {ch}")


client.run(os.environ["DISCORD_TOKEN"])
