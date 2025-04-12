import os
import time
import logging
import threading
import requests
from flask import Flask, request
import telebot
from telebot import types
from dotenv import load_dotenv
from collections import deque

# === Load environment variables ===
load_dotenv()

TOKEN = os.environ.get("TOKEN")
GROUP_CHAT_ID = os.environ.get("GROUP_CHAT_ID")
PORT = int(os.environ.get("PORT", 8483))

if not TOKEN or not GROUP_CHAT_ID:
    raise ValueError("TOKEN and GROUP_CHAT_ID must be set, you magnificent twat.")

# === Initialize Flask and Bot ===
app = Flask(__name__)
bot = telebot.TeleBot(TOKEN)
user_data = {}
recent_updates = deque(maxlen=100)

# === Logging ===
logging.basicConfig(level=logging.INFO)

# === Health check endpoint ===
@app.route("/", methods=["GET"])
def health():
    return "Bot is alive and sexy!", 200

# === Webhook endpoint ===
@app.route(f"/{TOKEN}", methods=["POST"])
def telegram_webhook():
    json_str = request.stream.read().decode("utf-8")
    update = telebot.types.Update.de_json(json_str)

    if update.update_id in recent_updates:
        logging.info(f"\U0001F501 Duplicate update ignored: {update.update_id}")
        return "OK", 200

    recent_updates.append(update.update_id)
    bot.process_new_updates([update])
    logging.info("\U0001F4E9 Webhook received and processed.")
    return "OK", 200

# === Keep-Alive Ping ===
def keep_alive():
    while True:
        try:
            requests.get("https://chatbot32-production.up.railway.app/")
        except Exception as e:
            logging.warning("Keep-alive ping failed: %s", e)
        time.sleep(300)

threading.Thread(target=keep_alive, daemon=True).start()

# === Spam Keywords ===
SPAM_KEYWORDS = ["vpn", "@speeeedvpnbot", "🔥", "t.me", "bot", "7 дней", "бесплатно", "поддерживаются"]

def is_spam(text):
    return any(keyword in text.lower() for keyword in SPAM_KEYWORDS)

# === /start Command ===
@bot.message_handler(commands=['start'])
def start_handler(message):
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
    button = types.KeyboardButton("📱 أرسل رقم هاتفك", request_contact=True)
    markup.add(button)
    bot.send_message(message.chat.id, "مرحباً! الرجاء إرسال رقم هاتفك بالضغط على الزر أدناه للمتابعة.", reply_markup=markup)

# === Handle Contact ===
@bot.message_handler(content_types=["contact"])
def contact_handler(message):
    phone = message.contact.phone_number
    user_data[message.chat.id] = {"phone": phone}
    bot.send_message(
        message.chat.id,
        f"📞 تم استلام رقم هاتفك بنجاح: {phone}\nأرسل الآن نوع الأسمنت والكمية المطلوبة."
    )
    logging.info(f"📱 Contact saved: {phone} for user {message.chat.id}")

# === Handle Orders ===
@bot.message_handler(func=lambda m: m.text and not m.text.startswith("/"))
def order_handler(message):
    user = message.from_user
    text = message.text
    chat_id = message.chat.id

    if user.is_bot or is_spam(text):
        logging.warning(f"⚠️ Spam or bot message ignored: {text}")
        return

    phone = user_data.get(chat_id, {}).get("phone")
    if not phone:
        logging.info(f"⛔️ User {chat_id} has not submitted a phone number.")
        return

    order_msg = (
        f"📦 طلب جديد:\n"
        f"👤 الاسم: {user.first_name or ''} {user.last_name or ''}\n"
        f"🆔 المستخدم: @{user.username or 'لا يوجد'}\n"
        f"📞 الهاتف: {phone}\n"
        f"📝 الطلب: {text}"
    )

    bot.send_message(GROUP_CHAT_ID, order_msg)
    bot.send_message(chat_id, "✅ تم استلام طلبك بنجاح، سيتم التواصل معك قريباً.")
    logging.info(f"📤 Order forwarded from {chat_id}")

# === /myrequests placeholder ===
@bot.message_handler(commands=["myrequests"])
def myrequests_handler(message):
    bot.send_message(message.chat.id, "📂 هذه الميزة تحت التطوير حالياً، تابعنا للمزيد!")

# === Webhook setup ===
webhook_url = f"https://chatbot32-production.up.railway.app/{TOKEN}"
bot.remove_webhook()
time.sleep(1)
bot.set_webhook(url=webhook_url)
logging.info(f"📡 Webhook set to {webhook_url}")


if __name__ == "__main__":
    from waitress import serve
    webhook_url = f"https://chatbot32-production.up.railway.app/{TOKEN}"
    bot.remove_webhook()
    time.sleep(1)
    bot.set_webhook(url=webhook_url)
    logging.info(f"📡 Webhook set to {webhook_url}")
    serve(app, host="0.0.0.0", port=PORT)
    app = app