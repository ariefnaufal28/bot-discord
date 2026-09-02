import os
import discord
from discord.ext import commands
from groq import Groq
from dotenv import load_dotenv

load_dotenv()

DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")
GROQ_API_KEY = os.getenv("GROQ_API_KEY")

groq_client = Groq(api_key=GROQ_API_KEY)

MODEL = "openai/gpt-oss-120b"  # model gratis di Groq, kuat buat coding
VISION_MODEL = "qwen/qwen3.6-27b"  # model gratis di Groq yang bisa baca gambar

IMAGE_EXTENSIONS = (".png", ".jpg", ".jpeg", ".webp", ".gif")

SYSTEM_PROMPT = (
    "Kamu adalah asisten pribadi yang membantu di server Discord, dengan keahlian khusus di coding. "
    "Jawab pertanyaan secara langsung dan natural sesuai apa yang ditanya. "
    "Kalau user tanya hal umum, perhitungan, atau pertanyaan sehari-hari, jawab dengan kalimat "
    "biasa/langsung — JANGAN membuatkan kode kecuali user secara eksplisit minta kode/script/program. "
    "Kalau user memang minta bantuan coding atau minta kode, baru gunakan code block markdown "
    "(```bahasa\\nkode\\n```). "
    "Gunakan bahasa Indonesia kecuali diminta bahasa lain."
)

intents = discord.Intents.default()
intents.message_content = True  # WAJIB diaktifkan juga di Developer Portal

bot = commands.Bot(command_prefix="!", intents=intents)

# Menyimpan history percakapan per channel (simple, in-memory)
conversation_history = {}
MAX_HISTORY = 10  # jumlah pesan yang diingat per channel


def get_history(channel_id):
    if channel_id not in conversation_history:
        conversation_history[channel_id] = []
    return conversation_history[channel_id]


def ask_ai(channel_id, user_message):
    history = get_history(channel_id)
    history.append({"role": "user", "content": user_message})

    messages = [{"role": "system", "content": SYSTEM_PROMPT}] + history[-MAX_HISTORY:]

    response = groq_client.chat.completions.create(
        model=MODEL,
        messages=messages,
        temperature=0.7,
        max_tokens=1500,
    )

    reply = response.choices[0].message.content
    history.append({"role": "assistant", "content": reply})
    return reply


def ask_ai_with_image(channel_id, user_message, image_urls):
    """Kirim pertanyaan + gambar ke model vision Groq. Gambar dikirim via URL Discord langsung."""
    history = get_history(channel_id)

    content = [{"type": "text", "text": user_message or "Tolong jelaskan gambar ini."}]
    for url in image_urls[:5]:  # Groq maksimal 5 gambar per request
        content.append({"type": "image_url", "image_url": {"url": url}})

    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": content},
    ]

    response = groq_client.chat.completions.create(
        model=VISION_MODEL,
        messages=messages,
        temperature=0.7,
        max_tokens=1500,
    )

    reply = response.choices[0].message.content

    # Simpan versi teks saja ke history (model vision tidak perlu history gambar lama)
    history.append({"role": "user", "content": user_message or "[gambar]"})
    history.append({"role": "assistant", "content": reply})

    return reply


def split_message(text, limit=2000):
    """Discord max 2000 karakter per pesan, jadi kita pecah kalau kepanjangan."""
    chunks = []
    while len(text) > limit:
        split_at = text.rfind("\n", 0, limit)
        if split_at == -1:
            split_at = limit
        chunks.append(text[:split_at])
        text = text[split_at:]
    chunks.append(text)
    return chunks


@bot.event
async def on_ready():
    print(f"✅ Bot aktif sebagai {bot.user}")


@bot.event
async def on_message(message):
    if message.author.bot:
        return

    # Bot merespon kalau di-mention ATAU di DM
    is_mentioned = bot.user in message.mentions
    is_dm = isinstance(message.channel, discord.DMChannel)

    if is_mentioned or is_dm:
        content = message.content.replace(f"<@{bot.user.id}>", "").strip()

        # Cek apakah ada gambar yang di-attach
        image_urls = [
            att.url for att in message.attachments
            if att.filename.lower().endswith(IMAGE_EXTENSIONS)
        ]

        if not content and not image_urls:
            await message.reply("Halo! Ada yang bisa aku bantu soal coding? 👨‍💻")
            return

        async with message.channel.typing():
            try:
                if image_urls:
                    reply = ask_ai_with_image(message.channel.id, content, image_urls)
                else:
                    reply = ask_ai(message.channel.id, content)
                for chunk in split_message(reply):
                    await message.reply(chunk)
            except Exception as e:
                await message.reply(f"⚠️ Ada error: `{e}`")

    await bot.process_commands(message)


@bot.command(name="ask")
async def ask_command(ctx, *, question: str):
    """Contoh: !ask cara bikin fungsi rekursif di python"""
    async with ctx.typing():
        try:
            reply = ask_ai(ctx.channel.id, question)
            for chunk in split_message(reply):
                await ctx.reply(chunk)
        except Exception as e:
            await ctx.reply(f"⚠️ Ada error: `{e}`")


@bot.command(name="reset")
async def reset_command(ctx):
    """Reset history percakapan di channel ini"""
    conversation_history[ctx.channel.id] = []
    await ctx.reply("🔄 History percakapan direset!")


@bot.command(name="help_asisten")
async def help_command(ctx):
    text = (
        "**🤖 Bot Asisten Coding**\n"
        "- Mention aku `@BotAsisten <pertanyaan>` untuk tanya apapun\n"
        "- `!ask <pertanyaan>` — sama seperti mention\n"
        "- `!reset` — reset history percakapan di channel ini\n"
        "- Chat lewat DM juga bisa langsung tanpa mention\n"
        "- Attach gambar bareng mention untuk tanya soal gambar (screenshot error, diagram, dll)\n"
    )
    await ctx.reply(text)


if __name__ == "__main__":
    if not DISCORD_TOKEN or not GROQ_API_KEY:
        raise SystemExit("❌ DISCORD_TOKEN atau GROQ_API_KEY belum diset di file .env")
    bot.run(DISCORD_TOKEN)