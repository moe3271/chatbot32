import os
import time
import logging
import threading
import requests
from flask import Flask, request
import telebot
from telebot import types
from dotenv import load_dotenv

# === Load .env ===
load_dotenv()
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger()

logger.info("🔍 Bot script is importing...")

# === Read TOKEN from environment or raise error ===
TOKEN = os.environ.get("TOKEN")
if not TOKEN:
    raise ValueError("Missing Telegram BOT TOKEN!")

ADMIN_CHAT_ID = os.environ.get("ADMIN_CHAT_ID") or "-1002258136452"
WEBHOOK_URL = f"https://chatbot32-production.up.railway.app/{TOKEN}"

# === Global app object for Gunicorn ===
app = Flask(__name__)

# === Telegram Bot Setup ===
bot = telebot.TeleBot(TOKEN)

# === Track users who shared phone numbers ===
user_phones = set()

# === Spam Keywords ===
SPAM_KEYWORDS = [
    "vpn", "продвижение", "دعم", "ترويج", "subscribe", "مجاني", "click here", "buy now"
]

def is_spam(message):
    if message.from_user.is_bot:
        return True
    text = message.text.lower() if message.text else ""
    return any(word in text for word in SPAM_KEYWORDS)

@bot.message_handler(content_types=["contact"])
def handle_contact(message):
    if message.contact and message.contact.phone_number:
        user_phones.add(message.from_user.id)
        bot.reply_to(message, "تم حفظ رقمك بنجاح. الآن يمكنك إرسال طلبك.")
    else:
        bot.reply_to(message, "يرجى مشاركة رقم هاتفك.")

@bot.message_handler(commands=["myrequests"])
def handle_myrequests(message):
    if message.from_user.id in user_phones:
        bot.reply_to(message, "سيتم إرسال طلباتك السابقة هنا.")
    else:
        bot.reply_to(message, "يرجى أولاً إرسال رقم هاتفك.")

@bot.message_handler(func=lambda m: True, content_types=["text"])
def handle_order(message):
    logger.info(f"📨 Received message from {message.from_user.id}: {message.text}")
    
    if is_spam(message):
        logger.info(f"Ignored spam from {message.from_user.id}: {message.text}")
        return
    
    if message.from_user.id not in user_phones:
        bot.reply_to(message, "يرجى إرسال رقم هاتفك أولاً.")
        return

    order_text = f"""🆕 طلب جديد:
👤 {message.from_user.first_name}
🆔 {message.from_user.id}
💬 {message.text}"""
    
    bot.send_message(ADMIN_CHAT_ID, order_text)
    bot.reply_to(message, "✅ تم إرسال طلبك بنجاح.")
@app.route("/webhook", methods=["POST"])
def raw_webhook():
    try:
        # Get raw request body as text
        json_data = request.get_data(as_text=True)

        # Log the entire incoming Telegram payload
        logger.info(f"📥 RAW TELEGRAM PAYLOAD:\n{json_data}")

        return '', 200
    except Exception as e:
        logger.error(f"🔥 RAW Webhook crashed: {e}", exc_info=True)
        return "RAW Webhook error", 500

@app.route("/debug", methods=["GET"])
def debug():
    logger.info("🐛 /debug was called")
    return "Bot is alive!", 200

def set_webhook():
    try:
        success = bot.set_webhook(url=WEBHOOK_URL)
        logger.info(f"📡 Webhook set: {success} => {WEBHOOK_URL}")
    except Exception as e:
        logger.error(f"🔥 Failed to set webhook: {e}", exc_info=True)

def keep_alive():
    def ping():
        while True:
            try:
                requests.get(WEBHOOK_URL)
                logger.info("🔄 Pinged webhook.")
            except Exception as e:
                logger.warning(f"⚠️ Keep-alive ping failed: {e}")
            time.sleep(500)
    try:
        thread = threading.Thread(target=ping)
        thread.daemon = True
        thread.start()
    except Exception as e:
        logger.error(f"🔥 Keep-alive crashed: {e}", exc_info=True)

# === Always run these on import by Gunicorn ===
set_webhook()
keep_alive()