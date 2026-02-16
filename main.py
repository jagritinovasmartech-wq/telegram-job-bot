import os
import logging
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes

# Logging सेटअप (Railway logs में दिखेगा)
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
logger = logging.getLogger(__name__)

# BOT_TOKEN Railway Variables से पढ़ो
TOKEN = os.getenv("BOT_TOKEN")

if not TOKEN:
    logger.error("BOT_TOKEN नहीं मिला! Variables में BOT_TOKEN ऐड करो।")
    exit(1)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """/start कमांड पर जवाब भेजो"""
    user = update.effective_user
    await update.message.reply_text(
        f"नमस्ते {user.first_name}! 👋\n"
        "Jobfinder Bot चालू है।\n"
        "जॉब अलर्ट्स के लिए /jobs भेजो या कोई सवाल पूछो!\n"
        "मैं रोज नए जॉब्स ढूंढकर बताऊंगा।"
    )
    logger.info(f"User {user.id} ने /start भेजा")

def main() -> None:
    logger.info("Bot is starting polling...")  # Railway logs में दिखेगा

    # Application बनाओ
    application = Application.builder().token(TOKEN).build()

    # /start कमांड हैंडलर ऐड करो
    application.add_handler(CommandHandler("start", start))

    # और कमांड्स ऐड कर सकते हो, जैसे:
    # async def jobs(update, context):
    #     await update.message.reply_text("यहाँ जॉब लिस्ट आएगी...")
    # application.add_handler(CommandHandler("jobs", jobs))

    # Polling शुरू करो
    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    main()
