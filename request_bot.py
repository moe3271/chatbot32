import os
import logging
import threading
import requests
from dotenv import load_dotenv
from flask import Flask, request, jsonify
from telebot import TeleBot, types
from telebot.types import Update

# 🔌 Keep-alive mechanism for Railway deployments
def keep_alive():
    try:
        requests.get("https://chatbot32-production.up.railway.app/")
    except:
        pass
    threading.Timer(300, keep_alive).start()

keep_alive()

# 🧪 Load environment variables
load_dotenv()

TOKEN = os.getenv("TOKEN")
ADMIN_ID = os.getenv("ADMIN_ID")
GROUP_CHAT_ID = os.getenv("7116729508")  # 🧠 This is your group chat ID

if not TOKEN or not GROUP_CHAT_ID:
    raise ValueError("TOKEN و CHAT_ID يجب ضبطهما في ملف البيئة يا عبقري!")

WEBHOOK_URL = f"https://chatbot32-production.up.railway.app/{TOKEN}"

# 🎯 Logging configuration
logging.basicConfig(level=logging.DEBUG)

app = Flask(__name__)
bot = TeleBot(TOKEN)
user_data = {}

@app.route("/")
def home():
    return "البوت يعمل بنجاح 💡"

# 🚀 Arabic Start Command
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

# ☎️ Contact handler
@bot.message_handler(content_types=["contact"])
def contact_handler(message):
    if message.contact is not None:
        phone_number = message.contact.phone_number
        user_data[message.chat.id] = {"phone": phone_number}
        bot.send_message(
            message.chat.id,
            f"📞 تم استلام رقم هاتفك بنجاح: {phone_number}\nالرجاء إرسال نوع الأسمنت والكمية المطلوبة."
        )

# 🧾 Handle cement order
@bot.message_handler(func=lambda msg: True)
def handle_request(message):
    phone = user_data.get(message.chat.id, {}).get("phone")
    if not phone:
        bot.send_message(message.chat.id, "يرجى إرسال رقم هاتفك أولاً عن طريق الزر في الأسفل.")
        start(message)
        return

    order_text = f"طلب جديد:\n📞 رقم الهاتف: {phone}\n📦 الطلب: {message.text}"
    
    # ✅ Send to group
    bot.send_message(GROUP_CHAT_ID, order_text)
    
    # ✅ Respond to user
    bot.send_message(message.chat.id, "✅ تم استلام طلبك بنجاح، سنقوم بالتواصل معك قريباً.")

# 📬 Webhook route
@app.route(f"/{TOKEN}", methods=["POST"])
def webhook():
    try:
        logging.info("📩 Webhook hit!")
        logging.debug("🔍 Headers: %s", request.headers)
        logging.debug("📦 Raw Data: %s", request.data)

        if not request.is_json:
            return jsonify({"error": "الطلب غير صحيح، نحتاج JSON"}), 400

        update_data = request.get_json()
        logging.info("✅ Parsed update JSON: %s", update_data)

        if not update_data:
            return jsonify({"error": "الطلب فارغ"}), 400

        update = Update.de_json(update_data)
        bot.process_new_updates([update])
        return "OK", 200

    except Exception as e:
        logging.exception("💥 Exception during webhook handling")
        return jsonify({"error": str(e)}), 500

# 🧷 Webhook activation
@app.before_request
def activate_bot():
    if not getattr(app, 'webhook_set', False):
        bot.remove_webhook()
        bot.set_webhook(url=WEBHOOK_URL)
        app.webhook_set = True
        logging.info(f"📡 Webhook set to: {WEBHOOK_URL}")

# 🧭 Show routes
with app.test_request_context():
    print("📌 Registered Flask Routes:")
    print(app.url_map)

# 🏁 Run Flask App
if __name__ == "__main__":
    logging.info("🚀 Starting Flask app...")
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port)