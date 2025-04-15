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

telebot.logger.setLevel(logging.DEBUG)  # ✅ Enable detailed bot logs

logger.info("🔍 Bot script is importing...")

# === Read TOKEN from environment or raise error ===
TOKEN = os.environ.get("TOKEN")


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
    "vpn", "продвижение", "подписка", "пробный период", "click here", "buy now",
    "subscribe", "instagram", "youtube", "مجاني", "دعم", "ترويج", "@speeeedvpnbot"
]
@bot.message_handler(commands=['start'])
def handle_start(message):
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
    contact_button = types.KeyboardButton("📱 إرسال رقم الهاتف", request_contact=True)
    markup.add(contact_button)
    bot.send_message(message.chat.id, "👋 مرحباً! الرجاء الضغط على الزر لإرسال رقم هاتفك.", reply_markup=markup)
    
def is_spam(message):
    text = message.text.lower()
    return any(keyword in text for keyword in SPAM_KEYWORDS)

@bot.message_handler(content_types=["contact"])
def handle_contact(message):
    if message.contact and message.contact.phone_number:
        user_id = message.from_user.id
        user_phones.add(user_id)
         # 🪛 Debugging output
        print(f"✅ Stored phone for: {user_id}")
        print(f"📦 Current users: {user_phones}")
        bot.reply_to(message, "✅ تم تسجيل رقم هاتفك بنجاح. يمكنك الآن إرسال طلبك.")
    else:
        bot.reply_to(message, "❌ لم يتم استلام رقم الهاتف. حاول مرة أخرى.")

@bot.message_handler(commands=["myrequests"])
def handle_myrequests(message):
    if message.from_user.id in user_phones:
        bot.reply_to(message, "سيتم إرسال طلباتك السابقة هنا.")
    else:
        bot.reply_to(message, "يرجى أولاً إرسال رقم هاتفك.")

@bot.message_handler(func=lambda m: True, content_types=["text"])
def handle_order(message):
    user_id = message.from_user.id

    if is_spam(message):
        logger.info(f"🚫 Ignored spam from {user_id}: {message.text}")
        return

    if user_id not in user_phones:
        handle_start(message)
        return

    user_phone = user_phones.get(user_id, "📵 رقم غير متوفر")

    order_text = f"""🆕 طلب جديد:
👤 الاسم: {message.from_user.first_name}
🆔 المعرف: {user_id}
📞 الهاتف: {user_phone}
💬 الطلب: {message.text}"""

    logger.info(f"📤 Sending order to group: {order_text}")

    try:
        bot.send_message(ADMIN_CHAT_ID, order_text)
        bot.reply_to(message, "✅ تم إرسال طلبك بنجاح.")
    except Exception as e:
        logger.error(f"❌ Failed to send order to group: {e}", exc_info=True)
@app.route(f"/{TOKEN}", methods=["POST"])
def webhook():
    try:
        if request.headers.get("content-type") == "application/json":
            json_string = request.get_data().decode("utf-8")
            logger.info(f"📥 Incoming update: {json_string}")
            update = telebot.types.Update.de_json(json_string)
            bot.process_new_updates([update])
            return '', 200
        else:
            logger.warning("❌ Invalid content-type")
            return "Invalid content-type", 403
    except Exception as e:
        logger.error(f"🔥 Webhook crashed: {e}", exc_info=True)
        return "Webhook crashed", 500

@app.route("/webhook", methods=["POST"])
def raw_webhook():
    try:
        json_data = request.get_data(as_text=True)
        logger.info(f"📥 RAW TELEGRAM PAYLOAD:\n{json_data}")
        return '', 200
    except Exception as e:
        logger.error(f"🔥 RAW Webhook crashed: {e}", exc_info=True)
        return "RAW Webhook error", 500

@app.route("/debug", methods=["GET"])
def debug():
    logger.info("🤛 /debug was called")
    return "Bot is alive!", 200

def set_webhook():
    try:
        success = bot.set_webhook(url=WEBHOOK_URL)
        logger.info(f"📱 Webhook set: {success} ")
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
# === Run Flask app locally if executed directly ===
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    logger.info(f"🚀 Running locally on port {port}")
    app.run(host="0.0.0.0", port=port)