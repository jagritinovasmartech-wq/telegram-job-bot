import os
import logging
import feedparser
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes
from datetime import time

logging.basicConfig(format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO)
logger = logging.getLogger(__name__)

TOKEN = os.getenv("BOT_TOKEN")

if not TOKEN:
    logger.error("BOT_TOKEN नहीं मिला!")
    raise ValueError("BOT_TOKEN required")

# सरकारी जॉब्स और स्कीम्स के RSS फीड्स (अपडेटेड लिस्ट)
RSS_FEEDS = [
    "https://www.sarkariresult.com/rssfeed.xml",                 # Sarkari Result - जॉब्स
    "https://www.freejobalert.com/latest-jobs-rss-feed/",       # FreeJobAlert - लेटेस्ट जॉब्स
    "https://employmentnews.gov.in/rssfeed.xml",                # Employment News - सरकारी जॉब्स
    "https://www.indgovtjobs.in/feeds/posts/default",           # IndGovtJobs
    "https://biharhelp.in/feed/"                                # Bihar स्पेसिफिक (जॉब्स + स्कीम्स)
    # myscheme.gov.in का RSS अगर मिले तो ऐड करेंगे
]

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user
    await update.message.reply_text(
        f"नमस्ते {user.first_name}! 👋\n\n"
        "Jobfinder Bot चालू है! सरकारी जॉब्स और स्कीम्स अपडेट्स के लिए।\n\n"
        "कमांड्स:\n"
        "/jobs - सभी लेटेस्ट सरकारी जॉब्स की लिस्ट\n"
        "/subscribe - रोज अपडेट्स पाने के लिए\n"
        "/help - मदद"
    )

async def jobs(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """सभी सरकारी जॉब्स/स्कीम्स की लिस्ट दिखाओ"""
    await update.message.reply_text("लोड हो रहा है... सभी सरकारी जॉब्स और स्कीम्स लिस्ट तैयार हो रही है ⏳")

    message = "📰 **सरकारी जॉब्स और स्कीम्स की लिस्ट**\n\n(लेटेस्ट अपडेट्स RSS से)\n\n"

    found_any = False
    for feed_url in RSS_FEEDS:
        feed = feedparser.parse(feed_url)
        if feed.entries:
            found_any = True
            title = feed.feed.title or feed_url.split('//')[1].split('/')[0]
            message += f"**{title.upper()}**\n"
            for entry in feed.entries[:6]:  # टॉप 6 दिखाओ
                title = entry.title[:120]  # लंबा न हो
                link = entry.link
                published = entry.get('published', 'N/A')
                message += f"• {title}\n  प्रकाशित: {published}\n  {link}\n\n"
            message += "────────────────────\n\n"

    if not found_any:
        message += "अभी कोई नई अपडेट नहीं मिली। थोड़ी देर बाद /jobs ट्राई करें या कल सुबह चेक करें!"

    await update.message.reply_text(message)

async def subscribe(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    chat_id = update.effective_chat.id
    with open("subscribers.txt", "a") as f:
        f.write(f"{chat_id}\n")
    await update.message.reply_text("✅ आप सब्सक्राइब हो गए! रोज सुबह 8 बजे नए जॉब्स/स्कीम्स अपडेट्स मिलेंगे।")

async def daily_update(context: ContextTypes.DEFAULT_TYPE) -> None:
    bot = context.bot
    try:
        with open("subscribers.txt", "r") as f:
            chat_ids = [int(line.strip()) for line in f if line.strip()]
    except FileNotFoundError:
        logger.info("कोई सब्सक्राइब्ड यूजर नहीं")
        return

    message = "🌅 **आज के सरकारी जॉब्स और स्कीम्स अपडेट्स**\n\n"
    found = False

    for feed_url in RSS_FEEDS:
        feed = feedparser.parse(feed_url)
        if feed.entries:
            found = True
            title = feed.feed.title or feed_url
            message += f"**{title}**\n"
            for entry in feed.entries[:3]:
                message += f"• {entry.title}\n  {entry.link}\n\n"

    if not found:
        message += "आज कोई नई अपडेट नहीं। कल चेक करें!"

    for chat_id in chat_ids:
        try:
            await bot.send_message(chat_id=chat_id, text=message)
        except Exception as e:
            logger.error(f"{chat_id} को मैसेज नहीं भेजा: {e}")

def main() -> None:
    logger.info("Jobfinder Bot शुरू हो रहा है... 🚀")

    application = Application.builder().token(TOKEN).build()

    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("jobs", jobs))
    application.add_handler(CommandHandler("subscribe", subscribe))

    # रोज सुबह 8 बजे अपडेट (IST)
    job_queue = application.job_queue
    job_queue.run_daily(daily_update, time=time(8, 0, 0))

    logger.info("Polling शुरू... इंतजार Telegram मैसेज का")
    application.run_polling(allowed_updates=Update.ALL_TYPES, drop_pending_updates=True)

if __name__ == "__main__":
    main()
