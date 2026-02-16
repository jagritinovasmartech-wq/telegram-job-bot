import os
import logging
import feedparser
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes

# Logging सेटअप - Railway logs में सब दिखेगा
logging.basicConfig(format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO)
logger = logging.getLogger(__name__)

TOKEN = os.getenv("BOT_TOKEN")

if not TOKEN:
    logger.error("BOT_TOKEN नहीं मिला!")
    raise ValueError("BOT_TOKEN required")

# RSS फीड्स (Bihar + India सरकारी जॉब्स/स्कीम्स के लिए)
RSS_FEEDS = [
    "https://www.sarkariresult.com/rssfeed.xml",                 # Sarkari Result (जॉब्स)
    "https://www.freejobalert.com/latest-jobs-rss-feed/",       # FreeJobAlert
    "https://employmentnews.gov.in/rssfeed.xml",                # Employment News (सरकारी)
    "https://www.indgovtjobs.in/feeds/posts/default",           # IndGovtJobs
    "https://biharhelp.in/feed/"                                # Bihar Help (Bihar फोकस्ड)
]

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user
    await update.message.reply_text(
        f"नमस्ते {user.first_name}! 👋\n\n"
        "Jobfinder Bot चालू है।\n"
        "सरकारी जॉब्स, स्कीम्स और अपडेट्स के लिए बेस्ट बॉट!\n\n"
        "कमांड्स:\n"
        "/jobs - लेटेस्ट जॉब्स और स्कीम्स की लिस्ट\n"
        "/subscribe - रोज अपडेट्स पाने के लिए\n"
        "/help - मदद"
    )
    logger.info(f"User {user.id} ने /start भेजा")

async def jobs(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """लेटेस्ट जॉब्स/स्कीम्स दिखाओ"""
    await update.message.reply_text("लेटेस्ट जॉब्स और स्कीम्स लोड हो रहे हैं... ⏳")
    
    message = "📰 **लेटेस्ट सरकारी जॉब्स और स्कीम्स**\n\n"
    found = False

    for feed_url in RSS_FEEDS:
        feed = feedparser.parse(feed_url)
        if feed.entries:
            found = True
            message += f"**{feed.feed.title or 'RSS Feed'}**\n"
            for entry in feed.entries[:5]:  # टॉप 5
                title = entry.title[:100]  # लंबा न हो
                link = entry.link
                message += f"• {title}\n  {link}\n\n"

    if not found:
        message += "अभी कोई नई अपडेट नहीं। थोड़ी देर बाद ट्राई करें!"

    await update.message.reply_text(message)
    logger.info(f"User {update.effective_user.id} ने /jobs मांगा")

async def subscribe(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """रोज अपडेट्स के लिए सब्सक्राइब"""
    chat_id = update.effective_chat.id
    with open("subscribers.txt", "a") as f:
        f.write(f"{chat_id}\n")
    await update.message.reply_text("✅ आप सब्सक्राइब हो गए! रोज सुबह नए जॉब्स/स्कीम्स अपडेट्स मिलेंगे।")
    logger.info(f"User {chat_id} सब्सक्राइब हुआ")

def main() -> None:
    logger.info("Jobfinder Bot शुरू हो रहा है... 🚀")

    application = Application.builder().token(TOKEN).build()

    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("jobs", jobs))
    application.add_handler(CommandHandler("subscribe", subscribe))

    logger.info("Polling शुरू... Telegram से इंतजार")
    application.run_polling(allowed_updates=Update.ALL_TYPES, drop_pending_updates=True)

if __name__ == "__main__":
  import time  # रोज अपडेट के लिए

async def daily_update(context: ContextTypes.DEFAULT_TYPE) -> None:
    """रोज सुबह 8 बजे अपडेट भेजो"""
    bot = context.bot
    try:
        with open("subscribers.txt", "r") as f:
            chat_ids = [int(line.strip()) for line in f if line.strip()]
    except FileNotFoundError:
        chat_ids = []
        logger.info("कोई सब्सक्राइब्ड यूजर नहीं")
        return

    message = "🌅 आज के नए सरकारी जॉब्स और स्कीम्स अपडेट्स!\n\n"
    found = False

    for feed_url in RSS_FEEDS:
        feed = feedparser.parse(feed_url)
        if feed.entries:
            found = True
            message += f"**{feed.feed.title or 'Update'}**\n"
            for entry in feed.entries[:3]:  # टॉप 3
                message += f"• {entry.title}\n  {entry.link}\n\n"

    if not found:
        message += "आज कोई नई अपडेट नहीं। कल ट्राई करें!"

    for chat_id in chat_ids:
        try:
            await bot.send_message(chat_id=chat_id, text=message)
        except Exception as e:
            logger.error(f"User {chat_id} को मैसेज नहीं भेजा: {e}")  main(job_queue = application.job_queue
job_queue.run_daily(daily_update, time=time(8, 0, 0))  # सुबह 8 बजे IST)
