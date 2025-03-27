from dotenv import load_dotenv
import os
from telebot import TeleBot
from flask import Flask, request

load_dotenv()

TOKEN = os.getenv("TOKEN")
ADMIN_ID = os.getenv("ADMIN_ID")
WEBHOOK_URL = os.getenv("https://api.telegram.org/bot7953137361:AAEeUuW1K0YOgqe9qmeQo7AYb3UXsiI3qPc/setWebhook?url=https://telegram-bot-starter.up.railway.app/")
print("TOKEN =", TOKEN)
from telebot import TeleBot
bot = TeleBot(TOKEN)
app = Flask(__name__)
@app.route("/")
def home():
    return "Bot is running!"

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080)

user_data = {}

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
    # Send order to admin
    bot.send_message("YOUR_ADMIN_CHAT_ID", order_text)
    bot.send_message(message.chat.id, "✅ تم استلام طلبك بنجاح، سيتم التواصل معك قريباً.")

# Webhook route
@app.route(f"/{TOKEN}", methods=["POST"])
def webhook():
    bot.process_new_updates([types.Update.de_json(request.stream.read().decode("utf-8"))])
    return "OK", 200

# Set webhook on startup
@app.before_request
def activate_bot():
    if not getattr(app, 'webhook_set', False):
        bot.remove_webhook()
        bot.set_webhook(url=WEBHOOK_URL)
        app.webhook_set = True

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8443))
    app.run(host="0.0.0.0", port=port)