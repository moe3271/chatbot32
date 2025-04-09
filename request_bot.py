import os
import time
import logging
logging.basicConfig(level=logging.INFO)
import threading
import requests
from flask import Flask, request
import telebot
from telebot import types
from dotenv import load_dotenv

# === Load .env ===
load_dotenv()

TOKEN = os.environ.get('TOKEN')
ADMIN_CHAT_ID = os.environ.get('ADMIN_CHAT_ID')
GROUP_CHAT_ID = os.environ.get('GROUP_CHAT_ID')
PORT = int(os.environ.get("PORT", 8483))


if not TOKEN or not GROUP_CHAT_ID:
    raise ValueError("TOKEN and GROUP_CHAT_ID must be set, you magnificent twat.")

bot = telebot.TeleBot(TOKEN)
app = Flask(__name__)
@app.route("/", methods=["GET"])
def health_check():
    return "Bot is alive and sexy!", 200
recent_updates = set()
user_data = {}

# === Keep-alive Ping ===
def keep_alive():
    while True:
        try:
            requests.get("https://chatbot32-production.up.railway.app/")
        except Exception as e:
            print("Keep-alive error:", e)
        time.sleep(300)

threading.Thread(target=keep_alive, daemon=True).start()

# === Webhook Route ===
@app.route(f"/{TOKEN}", methods=["POST"])
def webhook():
    json_str = request.stream.read().decode("utf-8")
    update = telebot.types.Update.de_json(json_str)

    if update.update_id in recent_updates:
        print(f"🔁 Duplicate update ignored: {update.update_id}")
        return "OK", 200
    recent_updates.add(update.update_id)

    if len(recent_updates) > 100:
        recent_updates.pop()

    bot.process_new_updates([update])
    print("📩 Webhook hit!")
    return "OK", 200

# === /start Command ===
@bot.message_handler(commands=['start'])
def handle_start(message):
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
    button = types.KeyboardButton("📱 أرسل رقم هاتفك", request_contact=True)
    markup.add(button)
    bot.send_message(
        message.chat.id,
        "مرحباً! الرجاء إرسال رقم هاتفك بالضغط على الزر أدناه للمتابعة.",
        reply_markup=markup
    )

# === Handle Contact ===
@bot.message_handler(content_types=['contact'])
def handle_contact(message):
    phone = message.contact.phone_number
    user_data[message.chat.id] = {"phone": phone}
    bot.send_message(
        message.chat.id,
        f"📞 تم استلام رقم هاتفك بنجاح: {phone}\nأرسل الآن نوع الأسمنت والكمية المطلوبة."
    )

# === Spam Keywords ===
SPAM_KEYWORDS = ["vpn", "@speeeedvpnbot", "7 дней", "поддерживаются", "🔥", "бесплатно"]

def is_spam(text):
    return any(kw in text.lower() for kw in SPAM_KEYWORDS)

# === Handle Orders ===
@bot.message_handler(func=lambda m: m.text and not m.text.startswith("/"))
def handle_order(message):
    user_id = message.chat.id
    user = message.from_user
    text = message.text

    if user.is_bot:
        logging.info(f"🤖 Ignored message from bot user: {user_id}")
        return

    if is_spam(text):
        logging.warning("⚠️ Ignored suspected spam from %s: %s", user_id, text)
        return

    phone = user_data.get(user_id, {}).get("phone")
    if not phone:
        logging.info(f"⛔️ Ignored message from {user_id} — no phone on record.")
        return

    msg = (
        f"📦 طلب جديد:\n"
        f"👤 الاسم: {user.first_name or ''} {user.last_name or ''}\n"
        f"🆔 المستخدم: @{user.username or 'لا يوجد'}\n"
        f"📞 الهاتف: {phone}\n"
        f"📝 الطلب: {text}"
    )

    bot.send_message(GROUP_CHAT_ID, msg)
    bot.send_message(user_id, "✅ تم استلام طلبك بنجاح، سيتم التواصل معك قريباً.")

# === My Requests Placeholder ===
@bot.message_handler(commands=["myrequests"])
def handle_myrequests(message):
    bot.send_message(message.chat.id, "📂 هذه الميزة تحت التطوير حالياً، تابعنا للمزيد!")

# === Start the App ===
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)

    webhook_url = f"https://chatbot32-production.up.railway.app/{TOKEN}"
    bot.remove_webhook()
    time.sleep(1)
    bot.set_webhook(url=webhook_url)
    logging.info(f"📡 Webhook set to {webhook_url}")

    PORT = int(os.environ.get("PORT", "5000"))
    logging.info(f"🚀 Starting Flask app on port {PORT}")
    app.run(host="0.0.0.0", port=PORT)