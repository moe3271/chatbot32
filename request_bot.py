import os
import logging
import threading
import requests
from flask import Flask, request
import telebot
from telebot import types
from dotenv import load_dotenv

# === Load .env ===
load_dotenv()

TOKEN = os.environ.get("TOKEN") or "7953137361:AAGmZapPgoaFpLfsbjIBO8Tl8uEt8-LfWtg"
ADMIN_CHAT_ID = os.environ.get("ADMIN_CHAT_ID") or "-1002258136452"
WEBHOOK_URL = f"https://chatbot32-production.up.railway.app/{TOKEN}"

# === Global app object for Gunicorn ===
app = Flask(__name__)

# === Setup logging ===
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger()

# === Telegram Bot Setup ===
bot = telebot.TeleBot(TOKEN)

# === Track users who shared phone numbers ===
user_phones = set()

# === Spam Keywords (can be expanded) ===
SPAM_KEYWORDS = [
    "vpn", "продвижение", "دعم", "ترويج", "subscribe", "مجاني", "click here", "buy now"
]

# === Spam Check Function ===
def is_spam(message):
    if message.from_user.is_bot:
        return True
    text = message.text.lower() if message.text else ""
    return any(spam_word in text for spam_word in SPAM_KEYWORDS)

# === Contact Handler ===
@bot.message_handler(content_types=["contact"])
def handle_contact(message):
    if message.contact and message.contact.phone_number:
        user_phones.add(message.from_user.id)
        bot.reply_to(message, "تم حفظ رقمك بنجاح. الآن يمكنك إرسال طلبك.")
    else:
        bot.reply_to(message, "يرجى مشاركة رقم هاتفك.")

# === /myrequests Command ===
@bot.message_handler(commands=["myrequests"])
def handle_myrequests(message):
    if message.from_user.id in user_phones:
        bot.reply_to(message, "سيتم إرسال طلباتك السابقة هنا.")
    else:
        bot.reply_to(message, "يرجى أولاً إرسال رقم هاتفك.")

# === General Message Handler ===
@bot.message_handler(func=lambda m: True, content_types=["text"])
def handle_order(message):
    if is_spam(message):
        logger.info(f"Ignored spam from {message.from_user.id}: {message.text}")
        return

    if message.from_user.id not in user_phones:
        bot.reply_to(message, "يرجى إرسال رقم هاتفك أولاً.")
        return

    order_text = f"🆕 طلب جديد:\n👤 {message.from_user.first_name}\n🆔 {message.from_user.id}\n💬 {message.text}"
    bot.send_message(ADMIN_CHAT_ID, order_text)
    bot.reply_to(message, "✅ تم إرسال طلبك بنجاح.")

# === Flask Webhook Route ===
@app.route(f"/{TOKEN}", methods=["POST"])
def webhook():
    if request.headers.get("content-type") == "application/json":
        json_string = request.get_data().decode("utf-8")
        update = telebot.types.Update.de_json(json_string)
        bot.process_new_updates([update])
        return "", 200
    return "Invalid content type", 403

# === Set Webhook Automatically ===
def set_webhook():
    webhook_set = bot.set_webhook(url=WEBHOOK_URL)
    logger.info(f"📡 Webhook set to {WEBHOOK_URL}: {webhook_set}")

# === Keep-alive Ping to Prevent Railway Timeout ===
def keep_alive():
    def ping():
        while True:
            try:
                logger.info("🔄 Ping: sending self-request to keep Railway alive...")
                requests.get(WEBHOOK_URL)
            except Exception as e:
                logger.warning(f"⚠️ Keep-alive error: {e}")
            time.sleep(600)

    thread = threading.Thread(target=ping)
    thread.daemon = True
    thread.start()

# === Startup ===
if __name__ == "__main__":
    set_webhook()
    keep_alive()
 