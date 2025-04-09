import os
import time
import logging
import threading
import requests
from flask import Flask, request
import telebot
from telebot import types
from collections import deque
from dotenv import load_dotenv

# === ENVIRONMENT ===
load_dotenv()

TOKEN = os.getenv("TOKEN") or "7953137361:AAEeUuW1K0YOgqe9qmeQo7AYb3UXsiI3qPc"
GROUP_CHAT_ID = os.getenv("GROUP_CHAT_ID") or "-1002258136452"
PORT = int(os.getenv("PORT", 8483))

if not TOKEN or not GROUP_CHAT_ID:
    raise ValueError("TOKEN and GROUP_CHAT_ID must be set, you magnificent twat.")

bot = telebot.TeleBot(TOKEN)
app = Flask(__name__)
user_data = {}
recent_updates = deque(maxlen=100)

# === KEEP ALIVE THREAD ===
def keep_alive():
    while True:
        try:
            requests.get("https://chatbot32-production.up.railway.app/")
        except Exception as e:
            logging.warning("Keep-alive ping failed: %s", e)
        time.sleep(300)

threading.Thread(target=keep_alive, daemon=True).start()

# === SPAM FILTER ===
SPAM_KEYWORDS = [
    "vpn", "@speeeedvpnbot", "🔥", "t.me", "bot",
    "7 дней", "абсолютно", "бесплатно", "поддерживаются"
]

def is_spam(text):
    text = text.lower()
    return any(kw in text for kw in SPAM_KEYWORDS)

# === HEALTH CHECK ROUTE ===
@app.route("/", methods=["GET"])
def health_check():
    return "Bot is alive and sexy.", 200

# === WEBHOOK ROUTE ===
@app.route(f"/{TOKEN}", methods=["POST"])
def webhook():
    json_str = request.stream.read().decode("utf-8")
    update = telebot.types.Update.de_json(json_str)

    if update.update_id in recent_updates:
        return "OK", 200
    recent_updates.append(update.update_id)

    bot.process_new_updates([update])
    return "OK", 200

# === /start COMMAND ===
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

# === CONTACT HANDLER ===
@bot.message_handler(content_types=['contact'])
def handle_contact(message):
    if message.contact is not None:
        phone = message.contact.phone_number
        user_data[message.chat.id] = {"phone": phone}
        bot.send_message(
            message.chat.id,
            f"📞 تم استلام رقم هاتفك بنجاح: {phone}\nأرسل الآن نوع الأسمنت والكمية المطلوبة."
        )
        logging.info("✅ Contact received from %s: %s", message.chat.id, phone)

# === ORDER HANDLER ===
@bot.message_handler(func=lambda m: m.text and not m.text.startswith("/"))
def handle_order(message):
    user_id = message.chat.id
    user = message.from_user
    text = message.text

    if user.is_bot:
        logging.info("🤖 Ignoring bot message from %s", user_id)
        return

    if is_spam(text):
        logging.warning("⚠️ SPAM BLOCKED from %s: %s", user_id, text)
        return

    phone = user_data.get(user_id, {}).get("phone")
    if not phone:
        logging.info("❌ Ignoring message from %s: no phone number on file.", user_id)
        return

    msg = (
        f"📦 طلب جديد:\n"
        f"👤 الاسم: {user.first_name or ''} {user.last_name or ''}\n"
        f"🆔 المستخدم: @{user.username or 'لا يوجد'}\n"
        f"📞 الهاتف: {phone}\n"
        f"📋 الطلب: {text}"
    )

    bot.send_message(GROUP_CHAT_ID, msg)
    bot.send_message(user_id, "✅ تم استلام طلبك بنجاح، سيتم التواصل معك قريباً.")
    logging.info("📤 Order forwarded from %s", user_id)

# === PLACEHOLDER FOR MYREQUESTS ===
@bot.message_handler(commands=["myrequests"])
def handle_myrequests(message):
    bot.send_message(message.chat.id, "📂 هذه الميزة تحت التطوير حالياً، تابعنا للمزيد!")

# === RUN FLASK APP ===
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    webhook_url = f"https://chatbot32-production.up.railway.app/{TOKEN}"
    bot.remove_webhook()
    time.sleep(1)
    bot.set_webhook(url=webhook_url)
    logging.info(f"📡 Webhook set to {webhook_url}")
    app.run(host="0.0.0.0", port=PORT, debug=False)
