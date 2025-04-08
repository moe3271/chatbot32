import os
import time
import logging
import threading
import requests
from flask import Flask, request
import telebot
from telebot import types

# === ENVIRONMENT ===
TOKEN = os.environ.get("TOKEN")
GROUP_CHAT_ID = os.environ.get("GROUP_CHAT_ID")

if not TOKEN or not GROUP_CHAT_ID:
    raise ValueError("TOKEN and GROUP_CHAT_ID must be set, you magnificent twat.")

bot = telebot.TeleBot(TOKEN)
app = Flask(__name__)
user_data = {}
recent_updates = set()

# === KEEP ALIVE ===
def keep_alive():
    while True:
        try:
            requests.get("https://chatbot32-production.up.railway.app/")
        except Exception as e:
            logging.warning("Keep-alive ping failed: %s", e)
        time.sleep(300)

threading.Thread(target=keep_alive, daemon=True).start()

# === WEBHOOK ROUTE ===
@app.route(f"/{TOKEN}", methods=["POST"])
def webhook():
    json_str = request.stream.read().decode("utf-8")
    update = telebot.types.Update.de_json(json_str)

    if update.update_id in recent_updates:
        return "OK", 200
    recent_updates.add(update.update_id)

    if len(recent_updates) > 100:
        recent_updates.pop()

    bot.process_new_updates([update])
    return "OK", 200

# === /start ===
@bot.message_handler(commands=['start'])
def handle_start(message):
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
    button = types.KeyboardButton("📱 أرسل رقم هاتفك", request_contact=True)
    markup.add(button)
    bot.send_message(
        message.chat.id,
        "مرحباً! الرجاء إرسال رقم هاتفك للمتابعة.",
        reply_markup=markup
    )

# === Contact Handler ===
@bot.message_handler(content_types=['contact'])
def handle_contact(message):
    if message.contact is not None:
        phone = message.contact.phone_number
        user_data[message.chat.id] = {"phone": phone}
        bot.send_message(message.chat.id, f"📞 تم استلام رقم هاتفك بنجاح: {phone}\nأرسل الآن نوع الأسمنت والكمية المطلوبة.")

# === Spam Filter ===
SPAM_KEYWORDS = ["vpn", "@speeeedvpnbot", "7 дней", "поддерживаются", "🔥", "абсолютно бесплатно"]

def is_spam(text):
    text = text.lower()
    return any(kw in text for kw in SPAM_KEYWORDS)

# === Request Handler ===
@bot.message_handler(func=lambda m: m.text and not m.text.startswith("/"))
def handle_request(message):
    user_id = message.chat.id
    user = message.from_user
    text = message.text

    if is_spam(text):
        logging.warning("⚠️ SPAM BLOCKED: %s", text)
        return

    phone = user_data.get(user_id, {}).get("phone")
    if not phone:
        return  # Do not respond if phone isn't stored

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

# === RUN APP ===
if __name__ == "__main__":
    webhook_url = f"https://chatbot32-production.up.railway.app/{TOKEN}"
    bot.remove_webhook()
    time.sleep(1)
    bot.set_webhook(url=webhook_url)
    logging.info(f"📡 Webhook set to {webhook_url}")
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))