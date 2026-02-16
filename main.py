import os
import logging
import feedparser
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application, CommandHandler, MessageHandler,
    CallbackQueryHandler, ContextTypes, filters
)
from google import genai

# ── CONFIG ──────────────────────────────────────────────────────────
TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN", "YOUR_TOKEN")
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "YOUR_GEMINI_KEY")

logging.basicConfig(format="%(asctime)s - %(levelname)s - %(message)s", level=logging.INFO)
logger = logging.getLogger(__name__)

genai.configure(api_key=GEMINI_API_KEY)
model = genai.GenerativeModel("gemini-1.5-flash")
user_chats: dict = {}

JARVIS_PROMPT = """Tu JARVIS hai — India ka #1 Sarkari Job AI Expert.
1. Hindi aur English dono mein baat kar (user jis language mein pooche)
2. Sarkari naukri, SSC, UPSC, Railway, Banking, Police, Teaching, Defence jobs expert hai
3. Government schemes (PM schemes, state schemes) bhi batata hai
4. Har jawab mein emojis use kar
5. Job sawaalon mein: naam, eligibility, official website link do
6. Short, crisp aur helpful answers do
Tu India ka best job finder AI hai!"""

CATEGORY_FEEDS = {
    "banking":  "https://www.freejobalert.com/bank-jobs/feed/",
    "railway":  "https://www.freejobalert.com/railway-jobs/feed/",
    "ssc":      "https://www.freejobalert.com/ssc-jobs/feed/",
    "upsc":     "https://www.freejobalert.com/upsc-jobs/feed/",
    "state":    "https://www.freejobalert.com/state-govt-jobs/feed/",
    "police":   "https://www.freejobalert.com/police-jobs/feed/",
    "teaching": "https://www.freejobalert.com/teaching-jobs/feed/",
    "defence":  "https://www.freejobalert.com/defence-jobs/feed/",
}

CAT_NAMES = {
    "banking": "🏦 Banking Jobs", "railway": "🚂 Railway Jobs",
    "ssc": "📚 SSC Jobs",         "upsc": "🎖️ UPSC Jobs",
    "teaching": "🏫 Teaching Jobs","defence": "🛡️ Defence Jobs",
    "state": "🏛️ State Govt Jobs","police": "👮 Police Jobs"
}

# ── RSS FETCH ────────────────────────────────────────────────────────
def fetch_jobs(feed_url: str, max_items: int = 8) -> list:
    try:
        feed = feedparser.parse(feed_url)
        jobs = []
        for entry in feed.entries[:max_items]:
            jobs.append({
                "title": entry.get("title", "No Title"),
                "link": entry.get("link", "#"),
                "published": entry.get("published", "")[:16] if entry.get("published") else "",
            })
        return jobs
    except Exception as e:
        logger.error(f"RSS error: {e}")
        return []

def format_jobs(jobs: list, title: str = "🏛️ Latest Govt Jobs"):
    if not jobs:
        return "❌ Koi job nahi mili. Thodi der baad try karein.", InlineKeyboardMarkup([])
    text = f"*{title}*\n\n"
    buttons = []
    for i, job in enumerate(jobs[:8], 1):
        t = job['title'][:55] + "..." if len(job['title']) > 55 else job['title']
        text += f"*{i}.* {t}\n"
        if job.get('published'):
            text += f"   📅 {job['published']}\n"
        text += "\n"
        buttons.append([InlineKeyboardButton(f"🔗 {i}. Apply/Details", url=job['link'])])
    buttons.append([
        InlineKeyboardButton("🔄 Refresh", callback_data="all_jobs"),
        InlineKeyboardButton("📂 Categories", callback_data="show_categories")
    ])
    return text, InlineKeyboardMarkup(buttons)

# ── GEMINI AI CHAT ───────────────────────────────────────────────────
async def get_ai_response(user_id: int, message: str) -> str:
    try:
        if user_id not in user_chats:
            user_chats[user_id] = model.start_chat(history=[])
        chat = user_chats[user_id]
        full_message = f"{JARVIS_PROMPT}\n\nUser: {message}"
        response = chat.send_message(full_message)
        return response.text
    except Exception as e:
        logger.error(f"Gemini error: {e}")
        return "⚠️ AI temporarily unavailable. Please dobara try karo!"

# ── KEYBOARDS ────────────────────────────────────────────────────────
def main_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🏛️ Latest Jobs", callback_data="all_jobs"),
         InlineKeyboardButton("📂 Categories", callback_data="show_categories")],
        [InlineKeyboardButton("🎯 Banking", callback_data="cat_banking"),
         InlineKeyboardButton("🚂 Railway", callback_data="cat_railway")],
        [InlineKeyboardButton("📚 SSC", callback_data="cat_ssc"),
         InlineKeyboardButton("🎖️ UPSC", callback_data="cat_upsc")],
        [InlineKeyboardButton("🏫 Teaching", callback_data="cat_teaching"),
         InlineKeyboardButton("🛡️ Defence", callback_data="cat_defence")],
        [InlineKeyboardButton("❓ Help", callback_data="help_menu")],
    ])

# ── COMMANDS ─────────────────────────────────────────────────────────
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    name = update.effective_user.first_name or "Friend"
    msg = (
        f"🤖 *Namaste {name}! Main JARVIS hoon!*\n\n"
        f"Main tumhara personal *Sarkari Job Expert* hoon!\n\n"
        f"✅ Latest govt jobs dhundhna\n"
        f"✅ Eligibility batana\n"
        f"✅ Government schemes explain karna\n"
        f"✅ Exam preparation tips dena\n\n"
        f"💬 *Seedha pooch sakte ho — Hindi ya English mein!*\n"
        f"Ya neeche buttons use karo 👇"
    )
    await update.message.reply_text(msg, parse_mode="Markdown", reply_markup=main_keyboard())

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = (
        "🤖 *JARVIS — Help Menu*\n\n"
        "📌 *Commands:*\n"
        "/start — Bot shuru karo\n"
        "/jobs — Latest sarkari jobs\n"
        "/banking /railway /ssc /upsc\n"
        "/teaching /defence /state /police\n"
        "/clear — Chat history clear karo\n\n"
        "💬 *AI Chat:* Seedha koi bhi sawaal pooch!\n"
        "_Jaise: SSC tips do, Bihar schemes batao_"
    )
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("🏛️ Jobs Dekho", callback_data="all_jobs"),
         InlineKeyboardButton("🔙 Back", callback_data="back_start")]
    ])
    await update.message.reply_text(text, parse_mode="Markdown", reply_markup=keyboard)

async def jobs_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = await update.message.reply_text("⏳ Jobs load ho rahi hain...")
    jobs = fetch_jobs("https://www.freejobalert.com/feed/")
    text, keyboard = format_jobs(jobs, "🏛️ Latest Sarkari Jobs")
    await msg.edit_text(text, parse_mode="Markdown", reply_markup=keyboard, disable_web_page_preview=True)

async def cat_command(update, context, category: str):
    msg = await update.message.reply_text(f"⏳ {CAT_NAMES.get(category)} load ho rahi hain...")
    jobs = fetch_jobs(CATEGORY_FEEDS[category])
    text, keyboard = format_jobs(jobs, CAT_NAMES.get(category))
    await msg.edit_text(text, parse_mode="Markdown", reply_markup=keyboard, disable_web_page_preview=True)

async def banking_cmd(u, c): await cat_command(u, c, "banking")
async def railway_cmd(u, c): await cat_command(u, c, "railway")
async def ssc_cmd(u, c):     await cat_command(u, c, "ssc")
async def upsc_cmd(u, c):    await cat_command(u, c, "upsc")
async def teaching_cmd(u, c):await cat_command(u, c, "teaching")
async def defence_cmd(u, c): await cat_command(u, c, "defence")
async def state_cmd(u, c):   await cat_command(u, c, "state")
async def police_cmd(u, c):  await cat_command(u, c, "police")

async def clear_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_chats.pop(update.effective_user.id, None)
    await update.message.reply_text("🗑️ *Chat history clear ho gayi!* Fresh start 🚀", parse_mode="Markdown")

# ── BUTTON HANDLER ────────────────────────────────────────────────────
async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data

    if data == "all_jobs":
        await query.edit_message_text("⏳ Jobs load ho rahi hain...")
        jobs = fetch_jobs("https://www.freejobalert.com/feed/")
        text, keyboard = format_jobs(jobs, "🏛️ Latest Sarkari Jobs")
        await query.edit_message_text(text, parse_mode="Markdown", reply_markup=keyboard, disable_web_page_preview=True)

    elif data == "show_categories":
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("🏦 Banking", callback_data="cat_banking"),
             InlineKeyboardButton("🚂 Railway", callback_data="cat_railway")],
            [InlineKeyboardButton("📚 SSC", callback_data="cat_ssc"),
             InlineKeyboardButton("🎖️ UPSC", callback_data="cat_upsc")],
            [InlineKeyboardButton("🏫 Teaching", callback_data="cat_teaching"),
             InlineKeyboardButton("🛡️ Defence", callback_data="cat_defence")],
            [InlineKeyboardButton("🏛️ State Govt", callback_data="cat_state"),
             InlineKeyboardButton("👮 Police", callback_data="cat_police")],
            [InlineKeyboardButton("🔙 Back", callback_data="back_start")],
        ])
        await query.edit_message_text("📂 *Job Categories*\n\nKaunsi jobs dekhni hain?",
                                      parse_mode="Markdown", reply_markup=keyboard)

    elif data.startswith("cat_"):
        category = data.replace("cat_", "")
        if category in CATEGORY_FEEDS:
            await query.edit_message_text(f"⏳ {CAT_NAMES.get(category)} load ho rahi hain...")
            jobs = fetch_jobs(CATEGORY_FEEDS[category])
            text, keyboard = format_jobs(jobs, CAT_NAMES.get(category))
            await query.edit_message_text(text, parse_mode="Markdown", reply_markup=keyboard,
                                          disable_web_page_preview=True)

    elif data == "help_menu":
        keyboard = InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Back", callback_data="back_start")]])
        await query.edit_message_text(
            "🤖 *Help*\n\n/start /jobs /banking /railway /ssc /upsc\n/teaching /defence /state /police /clear\n\n"
            "💬 Seedha koi bhi sawaal pooch!", parse_mode="Markdown", reply_markup=keyboard)

    elif data == "back_start":
        await query.edit_message_text("🤖 *JARVIS — Main Menu*\n\nKya karna hai?",
                                      parse_mode="Markdown", reply_markup=main_keyboard())

# ── MESSAGE HANDLER ───────────────────────────────────────────────────
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    user_text = update.message.text.strip()
    await context.bot.send_chat_action(chat_id=update.effective_chat.id, action="typing")
    ai_reply = await get_ai_response(user_id, user_text)
    job_keywords = ["job", "naukri", "vacancy", "bharti", "recruitment", "sarkari"]
    if any(kw in user_text.lower() for kw in job_keywords):
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("🏛️ Latest Jobs", callback_data="all_jobs"),
             InlineKeyboardButton("📂 Categories", callback_data="show_categories")]
        ])
        await update.message.reply_text(ai_reply, parse_mode="Markdown", reply_markup=keyboard)
    else:
        await update.message.reply_text(ai_reply, parse_mode="Markdown")

async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE):
    logger.error(f"Error: {context.error}")

# ── MAIN ──────────────────────────────────────────────────────────────
def main():
    app = Application.builder().token(TELEGRAM_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CommandHandler("jobs", jobs_command))
    app.add_handler(CommandHandler("banking", banking_cmd))
    app.add_handler(CommandHandler("railway", railway_cmd))
    app.add_handler(CommandHandler("ssc", ssc_cmd))
    app.add_handler(CommandHandler("upsc", upsc_cmd))
    app.add_handler(CommandHandler("teaching", teaching_cmd))
    app.add_handler(CommandHandler("defence", defence_cmd))
    app.add_handler(CommandHandler("state", state_cmd))
    app.add_handler(CommandHandler("police", police_cmd))
    app.add_handler(CommandHandler("clear", clear_command))
    app.add_handler(CallbackQueryHandler(button_handler))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    app.add_error_handler(error_handler)
    logger.info("JARVIS Bot starting...")
    app.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    main()
