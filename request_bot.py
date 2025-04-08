import os
import telebot
from telebot import types
from flask import Flask, request
import threading
import requests
import time
import logging

# === Configuration ===
TOKEN = os.getenv('TOKEN')
GROUP_CHAT_ID = os.getenv('GROUP_CHAT_ID')

if not TOKEN or not GROUP_CHAT_ID:
    raise ValueError("TOKEN and GROUP_CHAT_ID must be set, you magnificent twat.")

bot = telebot.TeleBot(TOKEN)
app = Flask(__name__)
user_data = {}
recent_updates = set()

# === Logging ===
logging.basicConfig(level=logging.DEBUG)

# === Keep Alive ===
def keep_alive():
    while True:
        try:
            requests.get("https://chatbot32-production.up.railway.app/")
        except Exception as e:
            logging.error("Keep-alive error: %s", e)
        time.sleep(300)

threading.Thread(target=keep_alive, daemon=True).start()

# === Webhook ===
@app.route(f"/{TOKEN}", methods=["POST"])
def webhook():
    json_str = request.stream.read().decode("utf-8")
    update = telebot.types.Update.de_json(json_str)

    if update.update_id in recent_updates:
        logging.debug(f"🔁 Duplicate update ignored: {update.update_id}")
        return "OK", 200
    recent_updates.add(update.update_id)

    if len(recent_updates) > 100:
        recent_updates.pop()

    bot.process_new_updates([update])
    logging.info("📩 Webhook hit!")
    return "OK", 200

# === Start Command ===
@bot.message_handler(commands=['start'])
def handle_start(message):
    contact_button = types.KeyboardButton("📱 أرسل رقم هاتفك", request_contact=True)
    keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
    keyboard.add(contact_button)
    bot.send_message(
        message.chat.id,
        "مرحباً بك! الرجاء إرسال رقم هاتفك بالضغط على الزر أدناه.",
        reply_markup=keyboard
    )

# === Handle Contact ===
@bot.message_handler(content_types=['contact'])
def handle_contact(message):
    if message.contact:
        phone_number = message.contact.phone_number
        user_data[message.chat.id] = {"phone": phone_number}
        bot.send_message(
            message.chat.id,
            f"📞 تم استلام رقم هاتفك بنجاح: {phone_number}\nالرجاء الآن إرسال نوع الأسمنت والكمية المطلوبة."
        )

# === Handle Orders ===
@bot.message_handler(func=lambda m: m.text and not m.text.startswith("/") and not "@" in m.text and not m.text.lower().startswith("http"))
def handle_order(message):
    user_id = message.chat.id
    phone = user_data.get(user_id, {}).get("phone")

    # Only respond if phone number is saved
    if not phone:
        bot.send_message(user_id, "يرجى إرسال رقم هاتفك أولاً عبر الزر في الأسفل.")
        handle_start(message)
        return

    # Spam filtering
    spam_keywords = ["vpn", "@speeeedvpnbot", "7 дней", "поддерживаются", "🔥"]
    if any(kw in message.text.lower() for kw in spam_keywords):
        logging.warning("⚠️ Ignored suspected spam: %s", message.text)
        return

    user = message.from_user
    order_info = (
        f"📦 طلب جديد!\n\n"
        f"👤 الاسم: {user.first_name or ''} {user.last_name or ''}\n"
        f"🆔 المستخدم: @{user.username or 'لا يوجد'}\n"
        f"📞 الهاتف: {phone}\n"
        f"📝 الطلب: {message.text}"
    )

    bot.send_message(GROUP_CHAT_ID, order_info)
    bot.send_message(user_id, "✅ تم استلام طلبك بنجاح، سيتم التواصل معك قريباً.")

# === Optional: MyRequests Placeholder ===
@bot.message_handler(commands=['myrequests'])
def handle_myrequests(message):
    bot.send_message(message.chat.id, "📂 هذه الميزة تحت التطوير حالياً. تابعنا للمزيد!")

# === Launch ===
if __name__ == "__main__":
    webhook_url = f"https://chatbot32-production.up.railway.app/{TOKEN}"
    bot.remove_webhook()
    time.sleep(1)
    bot.set_webhook(url=webhook_url)
    logging.info(f"📡 Webhook set to {webhook_url}")
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))