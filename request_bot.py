import os
import logging
from dotenv import load_dotenv
from telebot import TeleBot, types
from telebot.types import Update
from flask import Flask, request, jsonify
import threading
def keep_alive():
    try:
        requests.get("https://your-bot-name.up.railway.app/")
    except:
        pass
    threading.Timer(300, keep_alive).start()

keep_alive()

# Load environment variables
load_dotenv()

# Retrieve Token and Admin ID from environment variables
TOKEN = os.getenv("TOKEN")
ADMIN_ID = os.getenv("ADMIN_ID")

if not TOKEN:
    raise ValueError("TOKEN is not set in environment variables!")

WEBHOOK_URL = f"https://chatbot32-production.up.railway.app/{TOKEN}"

# Logging, because we are professionals, not savages
logging.basicConfig(level=logging.DEBUG)

app = Flask(__name__)
bot = TeleBot(TOKEN)
user_data = {}

@app.route("/")
def home():
    return "Bot is running!"

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
    bot.send_message(ADMIN_ID, order_text)
    bot.send_message(message.chat.id, "✅ تم استلام طلبك بنجاح، سيتم التواصل معك قريباً.")

# Webhook route (DO NOT DUPLICATE THIS, you absolute rascal)
@app.route("/7953137361:AAEeUuW1K0YOgqe9qmeQo7AYb3UXsiI3qPc", methods=["POST"])
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
    bot.remove_webhook()
    bot.set_webhook(url=WEBHOOK_URL)
    logging.info(f"Webhook set to {WEBHOOK_URL}")

with app.test_request_context():
    print("📌 Registered Flask Routes:")
    print(app.url_map)

if __name__ == "__main__":
    logging.info("🚀 Starting Flask app...")
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port)



