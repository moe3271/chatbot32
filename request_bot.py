import os
import logging
from dotenv import load_dotenv
from telebot import TeleBot, types
from telebot.types import Update
from flask import Flask, request, jsonify
import threading
import requests

# 🔁 Keep-alive thread for Railway
def keep_alive():
    try:
        requests.get("https://chatbot32-production.up.railway.app/")
    except:
        pass
    threading.Timer(300, keep_alive).start()

keep_alive()

# 📦 Load environment variables
load_dotenv()
TOKEN = os.getenv("TOKEN")
ADMIN_ID = os.getenv("ADMIN_ID")
CHAT_ID = os.getenv("CHAT_ID")  # 🆕 Group chat ID from .env

if not TOKEN or not CHAT_ID:
    raise ValueError("TOKEN and CHAT_ID must be set in environment variables, you magnificent twat.")

WEBHOOK_URL = f"https://chatbot32-production.up.railway.app/{TOKEN}"

# 🧠 Logging like a proper gent
logging.basicConfig(level=logging.DEBUG)

app = Flask(__name__)
bot = TeleBot(TOKEN)
user_data = {}

@app.route("/")
def home():
    return "البوت يعمل بنجاح!"

@bot.message_handler(commands=["start"])
def start(message):
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
    button = types.KeyboardButton("📱 أرسل رقم هاتفك", request_contact=True)
    markup.add(button)
    bot.send_message(
        message.chat.id,
        "مرحباً! الرجاء إرسال رقم هاتفك للمتابعة.",
        reply_markup=markup
    )

@bot.message_handler(content_types=["contact"])
def contact_handler(message):
    if message.contact is not None:
        phone_number = message.contact.phone_number
        user_data[message.chat.id] = {"phone": phone_number}
        bot.send_message(
            message.chat.id,
            f"📞 تم استلام رقم هاتفك بنجاح: {phone_number}\nأرسل الآن نوع الأسمنت والكمية المطلوبة."
        )

@bot.message_handler(func=lambda msg: True)
def handle_request(message):
    phone = user_data.get(message.chat.id, {}).get("phone")
    if not phone:
        bot.send_message(message.chat.id, "يرجى إرسال رقم هاتفك أولاً بالضغط على الزر أدناه.")
        start(message)
        return

    order_text = f"طلب جديد:\n📞 رقم الهاتف: {phone}\n📦 الطلب: {message.text}"
    
    # ✉️ Send to admin
    bot.send_message(ADMIN_ID, order_text)

    # 📤 Send to group
    bot.send_message(CHAT_ID, order_text)

    bot.send_message(message.chat.id, "✅ تم استلام طلبك بنجاح، سيتم التواصل معك قريباً.")

@app.route(f"/{TOKEN}", methods=["POST"])
def webhook():
    try:
        logging.info("📩 Webhook hit! Telegram has arrived.")
        logging.debug("🔍 Headers: %s", request.headers)
        logging.debug("📦 Raw Data: %s", request.data)

        if not request.is_json:
            logging.warning("⛔️ Not a JSON payload!")
            return jsonify({"error": "Expected JSON"}), 400

        update_data = request.get_json()
        logging.info("✅ Parsed update JSON: %s", update_data)

        if not update_data:
            logging.warning("🤷‍♂️ Empty update received.")
            return jsonify({"error": "Empty request body"}), 400

        update = Update.de_json(update_data)
        bot.process_new_updates([update])
        return "OK", 200

    except Exception as e:
        logging.exception("💥 Exception while processing webhook")
        return jsonify({"error": str(e)}), 500

@app.before_request
def activate_bot():
    if not getattr(app, 'webhook_set', False):
        bot.remove_webhook()
        bot.set_webhook(url=WEBHOOK_URL)
        app.webhook_set = True
        logging.info(f"Webhook set to {WEBHOOK_URL}")

with app.test_request_context():
    print("📌 Registered Flask Routes:")
    print(app.url_map)

if __name__ == "__main__":
    logging.info("🚀 Starting Flask app...")
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port)




