import os
import logging
from dotenv import load_dotenv
from telebot import TeleBot, types
from telebot.types import Update
from flask import Flask, request, jsonify

# Load environment variables
load_dotenv()

# Retrieve Token and Admin ID from environment variables
TOKEN = os.getenv("TOKEN")
ADMIN_ID = os.getenv("ADMIN_ID")

# Ensure TOKEN is available
if not TOKEN:
    raise ValueError("TOKEN is not set in environment variables!")

# Webhook URL (Ensure this matches your deployed Railway App URL)
WEBHOOK_URL = f"https://telegram-bot-starter.up.railway.app/{TOKEN}"

# Configure logging
logging.basicConfig(level=logging.DEBUG)

# Initialize Flask
app = Flask(__name__)
bot = TeleBot(TOKEN)

# Store user data (phone numbers)
user_data = {}

@app.route("/")
def home():
    return "Bot is running!"

# Start command
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

# Handle contact (phone number)
@bot.message_handler(content_types=["contact"])
def contact_handler(message):
    if message.contact is not None:
        phone_number = message.contact.phone_number
        user_data[message.chat.id] = {"phone": phone_number}
        bot.send_message(
            message.chat.id,
            f"📞 تم استلام رقم هاتفك بنجاح: {phone_number}\nأرسل الآن نوع الأسمنت والكمية المطلوبة."
        )

# Handle cement request
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

# ✅ Webhook route — hardcoded to stop Telegram 404
@app.route("/7953137361:AAEeUuW1K0YOgqe9qmeQo7AYb3UXsiI3qPc", methods=["POST"])
def webhook():
    try:
        logging.debug("Received request: %s", request.data)

        if not request.is_json:
            logging.error("Invalid request: Not JSON")
            return jsonify({"error": "Invalid request, expected JSON"}), 400

        update_data = request.get_json()
        if not update_data:
            logging.error("Empty JSON received")
            return jsonify({"error": "Empty request body"}), 400

        update = Update.de_json(update_data)
        bot.process_new_updates([update])

        return "OK", 200
    except Exception as e:
        logging.exception("Error processing request")
        return jsonify({"error": str(e)}), 500

# Set webhook on startup
@app.before_request
def activate_bot():
    bot.remove_webhook()
    bot.set_webhook(url=WEBHOOK_URL)
    logging.info(f"Webhook set to {WEBHOOK_URL}")

# ✅ Print all registered routes in Railway logs
with app.test_request_context():
    print("📌 Registered Flask Routes:")
    print(app.url_map)

# Run the Flask server (required for Railway)
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8443))
    app.run(host="0.0.0.0", port=port)
