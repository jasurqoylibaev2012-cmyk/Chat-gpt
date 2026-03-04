import asyncio, logging, os, base64
from aiogram import Bot, Dispatcher, F, BaseMiddleware
from aiogram.types import Message, FSInputFile, BufferedInputFile, ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery, ErrorEvent, BotCommand
from aiogram.filters import CommandStart, Command
from aiogram.client.session.aiohttp import AiohttpSession
from aiogram.exceptions import TelegramForbiddenError
from dotenv import load_dotenv
from openai import OpenAI
import io, re, json
import numpy as np
import matplotlib.pyplot as plt
import matplotlib
import fitz # PyMuPDF
import yt_dlp
from duckduckgo_search import DDGS
matplotlib.use('Agg') # Non-interactive backend

logging.basicConfig(level=logging.INFO)
load_dotenv()

# Use proxy if provided (needed for PythonAnywhere free tier)
proxy_url = os.getenv("PROXY")
session = AiohttpSession(proxy=proxy_url) if proxy_url else None
bot = Bot(token=os.getenv("TELEGRAM_BOT_TOKEN"), session=session)
dp = Dispatcher()

# --- Error Handlers ---
@dp.error()
async def global_error_handler(event: ErrorEvent):
    if isinstance(event.exception, TelegramForbiddenError):
        user_id = "Unknown"
        if event.update.message:
            user_id = event.update.message.from_user.id
        elif event.update.callback_query:
            user_id = event.update.callback_query.from_user.id
        logging.warning(f"⚠️ Forbidden: Bot was blocked by user {user_id}. Ignoring this update.")
        return True
    
    logging.error(f"❌ Unhandled exception: {event.exception}", exc_info=event.exception)

# Configure OpenAI
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

ADMIN_ID = int(os.getenv("ADMIN_ID", 0))

import database as db

# --- Middleware ---
class BanCheckMiddleware(BaseMiddleware):
    async def __call__(self, handler, event, data):
        user = data.get("event_from_user")
        if user:
            db.add_user(user.id, user.username, user.full_name)
            if db.is_user_banned(user.id) and user.id != ADMIN_ID:
                if isinstance(event, Message):
                    await event.answer("🚫 Siz bloklanǵansız.")
                elif isinstance(event, CallbackQuery):
                    await event.answer("🚫 Siz bloklanǵansız.", show_alert=True)
                return
        return await handler(event, data)

dp.message.middleware(BanCheckMiddleware())
dp.callback_query.middleware(BanCheckMiddleware())

from datetime import datetime

# System prompt
current_date = datetime.now().strftime("%Y-%m-%d")
SYS_PROMPT = f"""You are JasurBot, a super-intelligent, friendly, and witty AI assistant created by the genius Qoylibaev Jasur. 🚀💻
Current Date: {current_date}

OFFICIAL BIO (Important):
If asked about 'Qoylibaev Jasur' or 'Jasur' (in any language), answer ONLY:
"Qoylibaev Jasur is the creator of this bot. He is a 13-year-old IT prodigy working at IT Park in Nukus. 👨‍💻✨"

CORE INSTRUCTIONS:
1.  **Visual Genius**: Analyze photos/documents in detail. Solve math step-by-step. 📸
2.  **Global Knowledge**: Deep and accurate info. 🌍
3.  **Language**: Expert in Karakalpak (Latin alphabet). prioritize Karakalpak. 🇰🇿🏛️
4.  **Memory**: Retain context from history.
5.  **Multimedia**: Use specialized modes for drawing, downloading, and searching.

IMPORTANT: You are connected to the internet. 
- If the context contains "SEARCH RESULTS", you MUST use that information to answer questions about today, news, or recent events. 
- IGNORE your internal knowledge cutoff (2025). 
- If the user asks about "today" or "latest news", DO NOT say "I don't have access". Instead, read the SEARCH RESULTS provided in the system message.
- Current Date is {current_date}. Treat this as the absolute truth.

🎨 **HTML FORMATTING ONLY**: <b>bold</b>, <i>italic</i>, <code>code</code>, <a href='url'>link</a>. NO MARKDOWN."""

# --- Keyboards ---
def get_main_kb():
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="💬 Chat"), KeyboardButton(text="🎨 Súwret")],
            [KeyboardButton(text="📥 Jüklew"), KeyboardButton(text="🌐 Izlew")],
            [KeyboardButton(text="🌍 Awdarma"), KeyboardButton(text="🗣️ Dawıs")],
            [KeyboardButton(text="📈 Grafik"), KeyboardButton(text="🧹 Yadı tazalaw")]
        ],
        resize_keyboard=True
    )

def get_lang_kb():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="English 🇺🇸", callback_data="setlang_en"),
         InlineKeyboardButton(text="Russian 🇷🇺", callback_data="setlang_ru")],
        [InlineKeyboardButton(text="Uzbek 🇺🇿", callback_data="setlang_uz"),
         InlineKeyboardButton(text="Karakalpak 🇰🇿", callback_data="setlang_qrk")]
    ])

# --- Commands ---
@dp.message(CommandStart())
async def s(m: Message):
    db.clear_history(m.from_user.id)
    db.set_user_mode(m.from_user.id, "chat")
    await m.answer("<b>Assalawma áleykum!</b> 👋\nMen tayarman! Túymeler arqalı xızmetlerden paydalanıń.", reply_markup=get_main_kb(), parse_mode="HTML")

@dp.message(F.text.contains("Chat"))
@dp.message(Command("chat"))
async def set_chat_mode(m: Message):
    db.set_user_mode(m.from_user.id, "chat")
    await m.answer("💬 <b>Chat rejimi kiritildi.</b> Sorawıńızdı jiberiń.", parse_mode="HTML", reply_markup=get_main_kb())

@dp.message(F.text.contains("Yadı tazalaw"))
@dp.message(Command("clear"))
async def clear_history_cmd(m: Message):
    db.clear_history(m.from_user.id)
    await m.answer("🧹 <b>Yad tazalandı!</b>", parse_mode="HTML")

@dp.message(F.text.contains("Súwret"))
@dp.message(Command("draw"))
async def draw_mode_handler(m: Message):
    db.set_user_mode(m.from_user.id, "draw")
    await m.answer("🎨 <b>Súwret sızıw rejimi kiritildi.</b> Ne sızayıq?", parse_mode="HTML")

@dp.message(F.text.contains("Jüklew"))
@dp.message(Command("download"))
async def download_mode_handler(m: Message):
    db.set_user_mode(m.from_user.id, "download")
    await m.answer("📥 <b>Jüklew rejimi kiritildi.</b> Siltew jiberiń!", parse_mode="HTML")

@dp.message(F.text.contains("Izlew"))
@dp.message(Command("search"))
async def search_mode_handler(m: Message):
    db.set_user_mode(m.from_user.id, "search")
    await m.answer("🌐 <b>Real-waqıtta izlew rejimi kiritildi.</b> Sorawıńızdı jiberiń.", parse_mode="HTML")

@dp.message(F.text.contains("Awdarma"))
@dp.message(Command("translate"))
async def translate_mode_handler(m: Message):
    db.set_user_mode(m.from_user.id, "translate")
    await m.answer("🌍 <b>Awdarma rejimi kiritildi.</b> Til saylań:", reply_markup=get_lang_kb(), parse_mode="HTML")

@dp.message(F.text.contains("Dawıs"))
@dp.message(Command("voice", "audio"))
async def voice_mode_handler(m: Message):
    db.set_user_mode(m.from_user.id, "voice")
    await m.answer("🗣️ <b>Dawıs rejimi kiritildi .</b> Tekst jiberiń.", parse_mode="HTML")

@dp.message(F.text.contains("Grafik"))
async def graph_btn_handler(m: Message):
    await m.answer("📈 Grafik sızıw ushın <code>/graph x**2</code> buyrıǵınan paydalanıń.", parse_mode="HTML")

@dp.callback_query(F.data.startswith("setlang_"))
async def set_lang_callback(c: CallbackQuery):
    lang_code = c.data.split("_")[1]
    db.set_user_lang(c.from_user.id, lang_code)
    await c.answer(f"Success!")
    await c.message.edit_text(f"✅ Til belgilenldi. Endi tekst jiberiń.", parse_mode="HTML")

@dp.message(Command("graph"))
async def graph_command(m: Message):
    expr = m.text.replace("/graph", "").strip()
    if not expr: return await m.answer("Usage: <code>/graph x**2</code>", parse_mode="HTML")
    await m.bot.send_chat_action(m.chat.id, "upload_photo")
    try:
        x = np.linspace(-10, 10, 500)
        y = eval(expr.replace("^", "**"), {"__builtins__": {}}, {"x": x, "np": np, "sin": np.sin, "cos": np.cos, "tan": np.tan})
        plt.figure(figsize=(8, 5)); plt.plot(x, y, color='#00aaff'); plt.grid(True)
        buf = io.BytesIO(); plt.savefig(buf, format='png'); buf.seek(0); plt.close()
        await m.answer_photo(BufferedInputFile(buf.read(), filename="graph.png"), caption=f"📈 y = <code>{expr}</code>", parse_mode="HTML")
    except Exception as e: await m.answer(f"❌ Error: {e}")

# --- Admin Commands ---

@dp.message(Command("users"), F.from_user.id == ADMIN_ID)
async def list_users(m: Message):
    users = db.get_users()
    if not users:
        return await m.answer("<b>Paydalanıshılar tabılmadı.</b>", parse_mode="HTML")
    
    count = len(users)
    msg = f"👤 <b>Paydalanıshılar dizimi ({count}):</b>\n\n"
    for uid, uname, fname, joined, active, banned in users:
        status = "🚫" if banned else "✅"
        uname_str = f" @{uname}" if uname else ""
        msg += f"{status} <code>{uid}</code> - {fname}{uname_str}\n"
    
    if len(msg) > 4096:
        for i in range(0, len(msg), 4096):
            await m.answer(msg[i:i+4096], parse_mode="HTML")
    else:
        await m.answer(msg, parse_mode="HTML")

@dp.message(Command("block"), F.from_user.id == ADMIN_ID)
async def block_user_cmd(m: Message):
    target_id = None
    if m.reply_to_message:
        target_id = m.reply_to_message.from_user.id
    else:
        parts = m.text.split()
        if len(parts) > 1:
            try:
                target_id = int(parts[1])
            except ValueError:
                return await m.answer("<b>ID qáte kiritildi.</b>", parse_mode="HTML")
    
    if target_id:
        db.ban_user(target_id)
        await m.answer(f"🚫 Paydalanıshı <code>{target_id}</code> bloklandı.", parse_mode="HTML")
    else:
        await m.answer("<b>Qollanılıwı:</b> <code>/block [user_id]</code> yamasa xatqa juwap jazıń.", parse_mode="HTML")

@dp.message(Command("unblock"), F.from_user.id == ADMIN_ID)
async def unblock_user_cmd(m: Message):
    target_id = None
    if m.reply_to_message:
        target_id = m.reply_to_message.from_user.id
    else:
        parts = m.text.split()
        if len(parts) > 1:
            try:
                target_id = int(parts[1])
            except ValueError:
                return await m.answer("<b>ID qáte kiritildi.</b>", parse_mode="HTML")
    
    if target_id:
        db.unban_user(target_id)
        await m.answer(f"✅ Paydalanıshı <code>{target_id}</code> bloktan shıǵarıldı.", parse_mode="HTML")
    else:
        await m.answer("<b>Qollanılıwı:</b> <code>/unblock [user_id]</code> yamasa xatqa juwap jazıń.", parse_mode="HTML")

# --- Logic Functions ---
async def search_logic(m: Message, query: str):
    await m.bot.send_chat_action(m.chat.id, "typing")
    try:
        results = []
        with DDGS() as ddgs:
            for r in ddgs.text(query, max_results=5): results.append(f"• <a href='{r['href']}'>{r['title']}</a>\n{r['body']}\n")
        context = "\n".join(results)
        if not context: return await m.answer("❌ Maǵlıwmat tawılmadı. (NSFW ya da qáwipsizlik süztesi sebebi bolıwı mómkin)")
        response = client.chat.completions.create(model="gpt-4o", messages=[{"role": "system", "content": SYS_PROMPT}, {"role": "user", "content": f"Search results for '{query}':\n\n{context}"}])
        await m.answer(f"🌐 <b>İzlew nátiyjeleri:</b>\n\n{response.choices[0].message.content}", parse_mode="HTML", disable_web_page_preview=True)
    except Exception as e: await m.answer(f"❌ Qátelik: {e}")

async def downloader_logic(m: Message, url: str):
    if "http" not in url: return await m.answer("❌ Siltew qáte!")
    st = await m.answer("📥 <b>Jüklenbekte...</b>"); await m.bot.send_chat_action(m.chat.id, "upload_video")
    ydl_opts = {
        'format': 'best', 'outtmpl': 'downloads/%(id)s.%(ext)s', 'max_filesize': 50*1024*1024,
        'http_headers': {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/119.0.0.0 Safari/537.36', 'Referer': 'https://www.instagram.com/'},
        'quiet': True, 'nocheckcertificate': True
    }
    if not os.path.exists("downloads"): os.makedirs("downloads")
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            fn = ydl.prepare_filename(info)
        await m.answer_video(FSInputFile(fn), caption=f"✅ <b>{info.get('title', 'Video')}</b>", parse_mode="HTML")
        os.remove(fn)
    except Exception: await m.answer("❌ Instagram/Social Media bizi blokladı. PythonAnywhere serverlerinde bul jiyis bolıp turadı.")

# --- Main Catch-All ---
@dp.message()
async def h(m: Message):
    if not m.text and not m.photo and not m.voice and not m.document: return
    if m.text and (m.text.startswith("/") or any(k in m.text for k in ["Chat", "Súwret", "Jüklew", "Izlew", "Awdarma", "Dawıs", "Yadı", "Grafik"])): return

    user_id = m.from_user.id
    mode = db.get_user_mode(user_id)
    if m.text:
        if mode == "draw": return await draw_command_logic(m, m.text)
        if mode == "download": return await downloader_logic(m, m.text)
        if mode == "search": return await search_logic(m, m.text)
        if mode == "translate": 
            langs = {"en": "English", "ru": "Russian", "uz": "Uzbek", "qrk": "Karakalpak"}
            res = client.chat.completions.create(model="gpt-4o", messages=[{"role": "user", "content": f"Translate to {langs.get(db.get_user_lang(user_id), 'Karakalpak')}: {m.text}"}])
            return await m.answer(f"🌐 <b>Awdarma:</b>\n\n<code>{res.choices[0].message.content}</code>", parse_mode="HTML")
        if mode == "voice":
            res = client.audio.speech.create(model="tts-1", voice="alloy", input=m.text)
            return await m.answer_voice(BufferedInputFile(res.content, filename="voice.ogg"))

    # Default Chat
    await m.bot.send_chat_action(m.chat.id, "typing")
    try:
        user_history = db.get_history(user_id, limit=15)
        user_content = []
        if m.voice:
            file_info = await bot.get_file(m.voice.file_id)
            voice_file = await bot.download_file(file_info.file_path)
            voice_buffer = io.BytesIO(voice_file.read()); voice_buffer.name = "v.ogg"
            tr = client.audio.transcriptions.create(model="whisper-1", file=voice_buffer)
            user_content.append({"type": "text", "text": f"[Voice]: {tr.text}"})
        if m.photo:
            photo = await bot.download(m.photo[-1])
            user_content.append({"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{base64.b64encode(photo.read()).decode('utf-8')}"}})
            user_content.append({"type": "text", "text": m.caption or "Analyze image."})
        if m.document:
            file_info = await bot.get_file(m.document.file_id); doc = await bot.download_file(file_info.file_path)
            ext = m.document.file_name.split('.')[-1].lower()
            text = ""
            if ext == "txt": text = doc.read().decode('utf-8', errors='ignore')
            elif ext == "pdf":
                with fitz.open(stream=doc.read(), filetype="pdf") as d:
                    for p in d: text += p.get_text()
            user_content.append({"type": "text", "text": f"[File]: {text[:3000]}"})
        if m.text: user_content.append({"type": "text", "text": m.text})
        
        # --- Auto-Search Logic ---
        db_txt = " ".join([p["text"] for p in user_content if p["type"]=="text"])
        search_context = ""
        keywords = ["2024", "2025", "2026", "2027", "bugun", "today", "news", "jańalıqlar", "weather", "ob-hawa", "kurs", "dollar", "futbol", "latest", "sońǵı"]
        
        # Configure env proxy for DDGS if needed
        if proxy_url:
            os.environ["HTTP_PROXY"] = proxy_url
            os.environ["HTTPS_PROXY"] = proxy_url

        if any(k in db_txt.lower() for k in keywords):
            try:
                await bot.send_chat_action(m.chat.id, "typing")
                # DDGS automatically picks up environment proxies
                with DDGS() as ddgs:
                    # Search specifically for "2026" or "current" if needed, but here searching the user prompt directly
                    s_res = [f"• {r['title']} - {r['body']}" for r in ddgs.text(db_txt, max_results=3)]
                if s_res:
                    search_context = "\nSEARCH RESULTS (Use this info for current events):\n" + "\n".join(s_res)
            except Exception as e:
                logging.error(f"Search failed: {e}")
                pass
        
        db.add_message(user_id, "user", db_txt.strip())
        
        sys_with_context = SYS_PROMPT
        if search_context: sys_with_context += f"\n\n{search_context}"
        
        msgs = [{"role": "system", "content": sys_with_context}] + [{"role": h["role"], "content": h["content"]} for h in user_history] + [{"role": "user", "content": user_content}]
        ans = client.chat.completions.create(model="gpt-4o", messages=msgs)
        db.add_message(user_id, "assistant", ans.choices[0].message.content)
        await m.answer(ans.choices[0].message.content, parse_mode="HTML")
    except Exception as e: await m.answer(f"Error: {e}")

async def draw_command_logic(m,p):
    await m.bot.send_chat_action(m.chat.id, "upload_photo")
    try:
        res = client.images.generate(model="dall-e-3", prompt=p)
        await m.answer_photo(res.data[0].url, caption=f"🎨 {p}")
    except Exception as e: await m.answer(f"❌ {e}")

async def main():
    await bot.set_my_commands([
        BotCommand(command="start", description="♻️ Restart bot"),
        BotCommand(command="chat", description="💬 Chat mode"),
        BotCommand(command="draw", description="🎨 Generate images"),
        BotCommand(command="download", description="📥 Download video"),
        BotCommand(command="search", description="🌐 Search web"),
        BotCommand(command="translate", description="🌍 Translate text"),
        BotCommand(command="voice", description="🗣️ Text to speech"),
        BotCommand(command="clear", description="🧹 Clear history"),
        BotCommand(command="graph", description="📈 Plot math function")
    ])
    await dp.start_polling(bot)
if __name__ == "__main__": asyncio.run(main())
