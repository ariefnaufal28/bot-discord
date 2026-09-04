import os
import re
import json
import requests
import discord
from datetime import datetime, timedelta, timezone
from discord.ext import commands
from groq import Groq
from dotenv import load_dotenv

load_dotenv()

DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
TAVILY_API_KEY = os.getenv("TAVILY_API_KEY")

groq_client = Groq(api_key=GROQ_API_KEY)

MODEL = "openai/gpt-oss-120b"  # model gratis di Groq, kuat buat coding
VISION_MODEL = "qwen/qwen3.6-27b"  # model gratis di Groq yang bisa baca gambar

IMAGE_EXTENSIONS = (".png", ".jpg", ".jpeg", ".webp", ".gif")

# Definisi tool "web_search" yang bisa dipanggil model kalau butuh info terkini
TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "web_search",
            "description": (
                "Cari informasi terkini di internet. Gunakan ini kalau user menanyakan "
                "sesuatu yang butuh data real-time atau terbaru, seperti kurs mata uang, "
                "harga, berita, cuaca, skor pertandingan, jadwal, atau fakta yang mungkin "
                "sudah berubah sejak data training kamu."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Kata kunci pencarian yang singkat dan spesifik.",
                    }
                },
                "required": ["query"],
            },
        },
    }
]

SYSTEM_PROMPT = (
    "Kamu adalah asisten pribadi yang membantu di server Discord, dengan keahlian khusus di coding. "
    "Jawab pertanyaan secara langsung dan natural sesuai apa yang ditanya. "
    "Kalau user tanya hal umum, perhitungan, atau pertanyaan sehari-hari, jawab dengan kalimat "
    "biasa/langsung — JANGAN membuatkan kode kecuali user secara eksplisit minta kode/script/program. "
    "Kalau user memang minta bantuan coding atau minta kode, baru gunakan code block markdown "
    "(```bahasa\\nkode\\n```). "
    "Kamu punya akses ke tool web_search untuk mencari info terkini (kurs, harga, berita, cuaca, "
    "jadwal, dan hal lain yang bisa berubah dari waktu ke waktu). Gunakan tool ini setiap kali "
    "pertanyaan butuh data terbaru atau kamu tidak yakin datamu masih akurat. "
    "Setelah dapat hasil pencarian, rangkum dan jawab berdasarkan hasil itu, sebutkan singkat "
    "kalau info ini dari pencarian terbaru. "
    "Kamu tidak punya akses untuk melihat riwayat aktivitas atau pesan user lain secara langsung "
    "lewat percakapan biasa. Kalau user bertanya soal aktivitas/riwayat chat orang lain di server "
    "(misal 'apa saja yang dilakukan si X'), arahkan mereka untuk pakai command "
    "`!activity @nama_user` yang bisa merangkum aktivitas chat user tersebut. "
    "Gunakan bahasa Indonesia kecuali diminta bahasa lain."
)

intents = discord.Intents.default()
intents.message_content = True  # WAJIB diaktifkan juga di Developer Portal
intents.members = True  # WAJIB diaktifkan juga di Developer Portal, untuk fitur !activity

bot = commands.Bot(command_prefix="!", intents=intents)

# Menyimpan history percakapan per channel (simple, in-memory)
conversation_history = {}
MAX_HISTORY = 10  # jumlah pesan yang diingat per channel


def get_history(channel_id):
    if channel_id not in conversation_history:
        conversation_history[channel_id] = []
    return conversation_history[channel_id]


def strip_thinking(text):
    """Buang blok <think>...</think> yang kadang muncul dari model reasoning."""
    cleaned = re.sub(r"<think>.*?</think>", "", text, flags=re.DOTALL)
    return cleaned.strip()


def web_search(query, max_results=4):
    """Cari info terkini pakai Tavily API. Return ringkasan hasil sebagai teks."""
    if not TAVILY_API_KEY:
        return "Web search tidak tersedia (TAVILY_API_KEY belum diset)."

    try:
        resp = requests.post(
            "https://api.tavily.com/search",
            json={
                "api_key": TAVILY_API_KEY,
                "query": query,
                "search_depth": "basic",
                "max_results": max_results,
                "include_answer": True,
            },
            timeout=15,
        )
        resp.raise_for_status()
        data = resp.json()
    except Exception as e:
        return f"Pencarian gagal: {e}"

    parts = []
    if data.get("answer"):
        parts.append(f"Ringkasan: {data['answer']}")

    for r in data.get("results", [])[:max_results]:
        title = r.get("title", "")
        content = r.get("content", "")[:400]
        url = r.get("url", "")
        parts.append(f"- {title}: {content} (sumber: {url})")

    return "\n".join(parts) if parts else "Tidak ada hasil ditemukan."


def run_with_tools(messages, model):
    """Jalankan chat completion dengan dukungan tool calling (web_search), loop sampai selesai."""
    for _ in range(4):  # batas maksimal 4 kali panggil tool berturut-turut, cegah infinite loop
        response = groq_client.chat.completions.create(
            model=model,
            messages=messages,
            tools=TOOLS,
            tool_choice="auto",
            temperature=0.7,
            max_tokens=1500,
        )
        msg = response.choices[0].message

        if not msg.tool_calls:
            return strip_thinking(msg.content or "")

        # Model minta panggil tool → jalankan lalu kirim hasilnya balik
        messages.append(msg)
        for tool_call in msg.tool_calls:
            if tool_call.function.name == "web_search":
                args = json.loads(tool_call.function.arguments)
                result = web_search(args.get("query", ""))
            else:
                result = "Tool tidak dikenali."

            messages.append({
                "role": "tool",
                "tool_call_id": tool_call.id,
                "content": result,
            })

    return "Maaf, terlalu banyak pencarian dibutuhkan untuk menjawab ini."


def ask_ai(channel_id, user_message):
    history = get_history(channel_id)
    history.append({"role": "user", "content": user_message})

    messages = [{"role": "system", "content": SYSTEM_PROMPT}] + history[-MAX_HISTORY:]

    reply = run_with_tools(messages, MODEL)
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

    reply = strip_thinking(response.choices[0].message.content)

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


async def collect_user_activity(guild, target_user, days=7, max_messages_per_channel=300):
    """Scan pesan dari target_user di semua text channel yang bisa diakses bot,
    dalam rentang `days` hari terakhir. Return list of {channel, content, timestamp}."""
    since = datetime.now(timezone.utc) - timedelta(days=days)
    collected = []

    for channel in guild.text_channels:
        # Skip channel yang bot gak punya izin baca
        perms = channel.permissions_for(guild.me)
        if not perms.read_message_history or not perms.view_channel:
            continue

        try:
            async for msg in channel.history(limit=max_messages_per_channel, after=since):
                if msg.author.id == target_user.id and not msg.author.bot:
                    collected.append({
                        "channel": channel.name,
                        "content": msg.content,
                        "timestamp": msg.created_at,
                    })
        except discord.Forbidden:
            continue
        except Exception:
            continue

    collected.sort(key=lambda x: x["timestamp"])
    return collected


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


@bot.command(name="activity")
async def activity_command(ctx, member: discord.Member, days: int = 7):
    """Contoh: !activity @user 7 — rangkum aktivitas chat user dalam N hari terakhir (default 7)"""
    if days < 1 or days > 30:
        await ctx.reply("Rentang hari harus antara 1-30.")
        return

    async with ctx.typing():
        await ctx.reply(f"🔍 Mengumpulkan aktivitas **{member.display_name}** dalam {days} hari terakhir...")

        messages = await collect_user_activity(ctx.guild, member, days=days)

        if not messages:
            await ctx.reply(
                f"Tidak ditemukan pesan dari **{member.display_name}** dalam {days} hari terakhir "
                f"(di channel yang bisa aku akses)."
            )
            return

        # Susun jadi teks ringkas buat dirangkum AI, batasi jumlah pesan biar gak kepanjangan
        log_lines = []
        for m in messages[-200:]:  # ambil maksimal 200 pesan terakhir biar gak overload
            ts = m["timestamp"].strftime("%d/%m %H:%M")
            content = m["content"][:200] if m["content"] else "[tanpa teks / attachment]"
            log_lines.append(f"[{ts}] #{m['channel']}: {content}")

        log_text = "\n".join(log_lines)

        summary_prompt = (
            f"Berikut adalah log pesan dari user '{member.display_name}' di server Discord "
            f"selama {days} hari terakhir ({len(messages)} pesan total). "
            f"Tolong rangkum aktivitas/topik yang dia bahas, pola waktu aktif, dan channel yang "
            f"paling sering dipakai. Jawab ringkas dalam poin-poin.\n\n{log_text}"
        )

        try:
            messages_payload = [
                {"role": "system", "content": "Kamu adalah asisten yang merangkum log chat menjadi ringkasan yang jelas dan ringkas."},
                {"role": "user", "content": summary_prompt},
            ]
            reply = run_with_tools(messages_payload, MODEL)
            reply = f"📊 **Ringkasan aktivitas {member.display_name} ({days} hari terakhir, {len(messages)} pesan):**\n\n{reply}"
            for chunk in split_message(reply):
                await ctx.reply(chunk)
        except Exception as e:
            await ctx.reply(f"⚠️ Gagal merangkum: `{e}`")


@activity_command.error
async def activity_command_error(ctx, error):
    if isinstance(error, commands.MemberNotFound):
        await ctx.reply("User tidak ditemukan. Pastikan kamu mention user-nya dengan benar, contoh: `!activity @nama_user`")
    elif isinstance(error, commands.MissingRequiredArgument):
        await ctx.reply("Format: `!activity @user [jumlah_hari]`, contoh: `!activity @budi 7`")
    else:
        await ctx.reply(f"⚠️ Error: `{error}`")


@bot.command(name="help_asisten")
async def help_command(ctx):
    text = (
        "**🤖 Bot Asisten Coding**\n"
        "- Mention aku `@BotAsisten <pertanyaan>` untuk tanya apapun\n"
        "- `!ask <pertanyaan>` — sama seperti mention\n"
        "- `!reset` — reset history percakapan di channel ini\n"
        "- Chat lewat DM juga bisa langsung tanpa mention\n"
        "- Attach gambar bareng mention untuk tanya soal gambar (screenshot error, diagram, dll)\n"
        "- Bisa cari info terkini otomatis (kurs, harga, berita, cuaca) lewat web search\n"
        "- `!activity @user [jumlah_hari]` — rangkum aktivitas chat user (default 7 hari)\n"
    )
    await ctx.reply(text)


if __name__ == "__main__":
    if not DISCORD_TOKEN or not GROQ_API_KEY:
        raise SystemExit("❌ DISCORD_TOKEN atau GROQ_API_KEY belum diset di file .env")
    bot.run(DISCORD_TOKEN)
