import os
import logging
import feedparser
from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    filters,
    ContextTypes,
)
from datetime import time

# Logging सेटअप
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
logger = logging.getLogger(__name__)

TOKEN = os.getenv("BOT_TOKEN")

if not TOKEN:
    logger.error("BOT_TOKEN नहीं मिला! Railway Variables में डालो।")
    raise ValueError("BOT_TOKEN required")

# RSS फीड्स (सरकारी जॉब्स + स्कीम्स)
RSS_FEEDS = [
    "https://www.sarkariresult.com/rssfeed.xml",
    "https://www.freejobalert.com/latest-jobs-rss-feed/",
    "https://employmentnews.gov.in/rssfeed.xml",
    "https://www.indgovtjobs.in/feeds/posts/default",
    "https://biharhelp.in/feed/",
]

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user
    await update.message.reply_text(
        f"नमस्ते {user.first_name}! 👋\n\n"
        "मैं Jobfinder AI हूँ – तुम्हारा पर्सनल सरकारी जॉब्स और स्कीम्स असिस्टेंट।\n\n"
        "तुम जो भी पूछोगे, मैं बताऊंगा:\n"
        "• Bihar sarkari naukri\n"
        "• PM Kisan scheme details\n"
        "• Latest RBI assistant apply kaise kare\n"
        "• Government jobs list\n\n"
        "कमांड्स:\n"
        "/jobs → सभी लेटेस्ट जॉब्स/स्कीम्स की लिस्ट\n"
        "/subscribe → रोज सुबह अपडेट्स\n"
        "/help → मदद"
    )

async def jobs(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text("लोड हो रहा है... सरकारी जॉब्स और स्कीम्स की लेटेस्ट लिस्ट तैयार हो रही है ⏳")

    message = "📰 **सरकारी जॉब्स और स्कीम्स की लेटेस्ट लिस्ट**\n(RSS अपडेट्स से)\n\n"

    found = False
    for feed_url in RSS_FEEDS:
        feed = feedparser.parse(feed_url)
        if feed.entries:
            found = True
            title = feed.feed.title or feed_url.split('//')[1].split('/')[0].upper()
            message += f"**{title}**\n"
            for entry in feed.entries[:8]:
                title = entry.title[:150]
                link = entry.link
                published = entry.get('published', 'N/A')
                message += f"• {title}\n  प्रकाशित: {published}\n  {link}\n\n"
            message += "────────────────────\n\n"

    if not found:
        message += "अभी कोई नई अपडेट नहीं। थोड़ी देर बाद ट्राई करें!"

    await update.message.reply_text(message)

async def subscribe(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    chat_id = update.effective_chat.id
    with open("subscribers.txt", "a") as f:
        f.write(f"{chat_id}\n")
    await update.message.reply_text(
        "✅ आप सब्सक्राइब हो गए!\nरोज सुबह 8 बजे नए जॉब्स, स्कीम्स और अपडेट्स मिलेंगे।"
    )

async def daily_update(context: ContextTypes.DEFAULT_TYPE) -> None:
    bot = context.bot
    try:
        with open("subscribers.txt", "r") as f:
            chat_ids = [int(line.strip()) for line in f if line.strip()]
    except FileNotFoundError:
        return

    message = "🌅 **आज के सरकारी जॉब्स और स्कीम्स अपडेट्स**\n\n"
    found = False

    for feed_url in RSS_FEEDS:
        feed = feedparser.parse(feed_url)
        if feed.entries:
            found = True
            title = feed.feed.title or feed_url
            message += f"**{title}**\n"
            for entry in feed.entries[:4]:
                message += f"• {entry.title}\n  {entry.link}\n\n"

    if not found:
        message += "आज कोई नई अपडेट नहीं। कल चेक करें!"

    for chat_id in chat_ids:
        try:
            await bot.send_message(chat_id=chat_id, text=message)
        except Exception as e:
            logger.error(f"{chat_id} को मैसेज नहीं भेजा: {e}")

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Agentic AI: हर मैसेज को समझकर जवाब देगा"""
    text = update.message.text.lower()
    user_id = update.effective_user.id
    logger.info(f"User {user_id} ने पूछा: {text}")

    # अगर जॉब या स्कीम से संबंधित है तो jobs दिखाओ
    if any(kw in text for kw in ["job", "naukri", "bharti", "vacancy", "scheme", "yojana", "स्कीम", "योजना", "list", "लिस्ट"]):
        await jobs(update, context)
        return

    # अगर सब्सक्राइब से संबंधित
    if any(kw in text for kw in ["subscribe", "सब्सक्राइब", "रोज अपडेट", "daily update"]):
        await subscribe(update, context)
        return

    # डिफॉल्ट स्मार्ट जवाब (ChatGPT जैसा फील)
    reply = (
        "समझ गया! सरकारी जॉब्स, स्कीम्स या अप्लाई प्रोसेस के बारे में पूछो।\n\n"
        "उदाहरण:\n"
        "• Bihar police bharti 2026\n"
        "• PM Kisan yojana kya hai\n"
        "• Latest government jobs list\n\n"
        "या सीधे /jobs भेजो!"
    )

    await update.message.reply_text(reply)

def main() -> None:
    logger.info("Agentic AI Jobfinder Bot शुरू हो रहा है... 🚀")

    application = Application.builder().token(TOKEN).build()

    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("jobs", jobs))
    application.add_handler(CommandHandler("subscribe", subscribe))

    # रोज सुबह 8 बजे अपडेट
    job_queue = application.job_queue
    if job_queue is None:
        logger.error("JobQueue नहीं मिला! requirements.txt में [job-queue] ऐड करो।")
    else:
        job_queue.run_daily(daily_update, time=time(8, 0, 0))

    # हर नॉन-कमांड मैसेज पर Agentic रिस्पॉन्स
    application.add_handler(
    MessageHandler(
        filters.TEXT & \~filters.COMMAND,
        handle_message
    )
    )

    logger.info("Polling शुरू... Telegram से बातचीत का इंतजार")
    application.run_polling(allowed_updates=Update.ALL_TYPES, drop_pending_updates=True)

if __name__ == "__main__":
    main()
