import os
import requests
from telegram import Bot
import time

TOKEN = os.getenv("BOT_TOKEN")
CHAT_ID = os.getenv("CHAT_ID")

bot = Bot(token=TOKEN)

def send_message(text):
    bot.send_message(chat_id=CHAT_ID, text=text)

if __name__ == "__main__":
    while True:
        send_message("🚀 New Govt Job Update Check Now!\n\nVisit official website for latest jobs & schemes.")
        time.sleep(3600)
