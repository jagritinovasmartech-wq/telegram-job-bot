import os
import logging
import feedparser
from google import genai
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.constants import ParseMode
from telegram.ext import (
    Application, CommandHandler, MessageHandler,
    CallbackQueryHandler, ContextTypes, filters
)

# ================== ENV CHECK ==================
TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")

if not TELEGRAM_TOKEN:
    raise ValueError("❌ TELEGRAM_TOKEN missing in environment variables")

if not GEMINI_API_KEY:
    raise ValueError("❌ GEMINI_API_KEY missing in environment variables")

# ================== LOGGING ==================
logging.basicConfig(
    format="%(asctime)s - %(levelname)s - %(message)s",
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# ================== GEMINI CLIENT ==================
client = genai.Client(api_key=GEMINI_API_KEY)

# ================== MEMORY CONTROL ==================
user_chats = {}
MAX_HISTORY = 6

# ================== AI SYSTEM PROMPT ==================
JARVIS_PROMPT = """Tu JARVIS hai — India ka #1 Sarkari Job AI Expert.
Rules:
1. Hindi + English mix me reply kar
2. Har jawab me emojis use kar
3. SSC, UPSC, Railway, Banking, Police, Defence expert hai
4. Government schemes bhi explain karta hai
5. Job answer me: Name, Eligibility, Official Website zaroor de
6. Short aur practical answer de
"""

# ================== JOB FEEDS ==================
MAIN_FEED = "https://www.freejobalert.com/feed/"

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
    "banking": "🏦 Banking Jobs",
    "railway": "🚂 Railway Jobs",
    "ssc": "📚 SSC Jobs",
    "upsc": "🎖️ UPSC Jobs",
    "teaching": "🏫 Teaching Jobs",
    "defence": "🛡️ Defence Jobs",
    "state": "🏛️ State Govt Jobs",
    "police": "👮 Police Jobs"
}

# ================== JOB FETCH ==================
def fetch_jobs(feed_url: str, limit: int = 6):
    try:
        feed = feedparser.parse(feed_url)
        jobs = []
        for entry in feed.entries[:limit]:
            jobs.append({
                "title": entry.get("title", "No Title"),
                "link": entry.get("link", "#"),
                "date": entry.get("published", "")[:16]
            })
        return jobs
    except Exception as e:
        logger.error(f"RSS Error: {e}")
        return []

def format_jobs(jobs, title="🏛️ Latest Jobs"):
    if not jobs:
        return "❌ Abhi koi job nahi mili. Thodi der baad try karo.", None

    text = f"*{title}*\n\n"
    buttons = []

    for i, job in enumerate(jobs, 1):
        text += f"{i}. {job['title']}\n📅 {job['date']}\n\n"
        buttons.append([InlineKeyboardButton(f"🔗 Apply {i}", url=job["link"])])

    buttons.append([
        InlineKeyboardButton("🔄 Refresh", callback_data="refresh"),
        InlineKeyboardButton("📂 Categories", callback_data="categories")
    ])

    return text, InlineKeyboardMarkup(buttons)

# ================== AI RESPONSE ==================
async def get_ai_response(user_id: int, message: str):

    if user_id not in user_chats:
        user_chats[user_id] = []

    user_chats[user_id].append(f"User: {message}")
    user_chats[user_id] = user_chats[user_id][-MAX_HISTORY:]

    full_prompt = JARVIS_PROMPT + "\n\n" + "\n".join(user_chats[user_id])

    try:
        response = client.models.generate_content(
            model="gemini-2.0-flash",
            contents=full_prompt
        )

        reply = getattr(response, "text", None)

        if not reply:
            reply = "⚠️ AI se response nahi mila. Dobara try karo."

        user_chats[user_id].append(f"JARVIS: {reply}")
        return reply

    except Exception as e:
        logger.error(f"Gemini Error: {e}")
        return "⚠️ AI temporarily busy hai. Thodi der baad try karo."

# ================== KEYBOARD ==================
def main_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🏛️ Latest Jobs", callback_data="refresh")],
        [InlineKeyboardButton("📂 Categories", callback_data="categories")],
        [InlineKeyboardButton("❓ Help", callback_data="help")]
    ])

# ================== COMMANDS ==================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🤖 *Namaste! Main JARVIS hoon — Sarkari Job Expert*\n\n"
        "💬 Seedha job ya exam ka sawaal pooch sakte ho!",
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=main_keyboard()
    )

async def jobs(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = await update.message.reply_text("⏳ Jobs load ho rahi hain...")
    jobs = fetch_jobs(MAIN_FEED)
    text, keyboard = format_jobs(jobs)
    await msg.edit_text(text, parse_mode=ParseMode.MARKDOWN, reply_markup=keyboard)

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    user_text = update.message.text

    await context.bot.send_chat_action(
        chat_id=update.effective_chat.id,
        action="typing"
    )

    reply = await get_ai_response(user_id, user_text)
    await update.message.reply_text(reply)

# ================== BUTTON HANDLER ==================
async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    if query.data == "refresh":
        jobs = fetch_jobs(MAIN_FEED)
        text, keyboard = format_jobs(jobs)
        await query.edit_message_text(text, parse_mode=ParseMode.MARKDOWN, reply_markup=keyboard)

    elif query.data == "categories":
        buttons = []
        for key, value in CAT_NAMES.items():
            buttons.append([InlineKeyboardButton(value, callback_data=f"cat_{key}")])
        buttons.append([InlineKeyboardButton("🔙 Back", callback_data="back")])

        await query.edit_message_text(
            "📂 *Select Category*",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=InlineKeyboardMarkup(buttons)
        )

    elif query.data.startswith("cat_"):
        category = query.data.replace("cat_", "")
        jobs = fetch_jobs(CATEGORY_FEEDS[category])
        text, keyboard = format_jobs(jobs, CAT_NAMES[category])
        await query.edit_message_text(text, parse_mode=ParseMode.MARKDOWN, reply_markup=keyboard)

    elif query.data == "back":
        await query.edit_message_text(
            "🤖 *Main Menu*",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=main_keyboard()
        )

# ================== MAIN ==================
def main():
    app = Application.builder().token(TELEGRAM_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("jobs", jobs))
    app.add_handler(CallbackQueryHandler(button_handler))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    logger.info("🚀 JARVIS Bot Running...")
    app.run_polling()

if __name__ == "__main__":
    main()
