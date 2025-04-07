import os
import telebot
from telebot import types
from flask import Flask, request
import threading
import requests
import time

# ==== Configuration ====
TOKEN = os.environ.get('TOKEN')
ADMIN_CHAT_ID = os.environ.get('ADMIN_CHAT_ID')
GROUP_CHAT_ID = os.environ.get('GROUP_CHAT_ID')

bot = telebot.TeleBot(TOKEN)
app = Flask(__name__)

# Cache to avoid processing duplicate updates
recent_updates = set()

# ==== Keep-alive Ping ====
def keep_alive():
    while True:
        try:
            requests.get(f"https://chatbot32-production.up.railway.app/")
        except Exception as e:
            print("Keep-alive error:", e)
        time.sleep(300)  # Every 5 minutes

threading.Thread(target=keep_alive, daemon=True).start()

# ==== Webhook Route ====
@app.route(f"/{TOKEN}", methods=["POST"])
def webhook():
    json_str = request.stream.read().decode("utf-8")
    update = telebot.types.Update.de_json(json_str)

    # Prevent duplicate processing
    if update.update_id in recent_updates:
        print(f"🔁 Duplicate update ignored: {update.update_id}")
        return "OK", 200
    recent_updates.add(update.update_id)

    # Clean up old entries in the cache (keep only latest 100)
    if len(recent_updates) > 100:
        recent_updates.pop()

    bot.process_new_updates([update])
    print("📩 Webhook hit!")
    return "OK", 200

# ==== Start Command ====
@bot.message_handler(commands=['start'])
def handle_start(message):
    contact_button = types.KeyboardButton("📱 أرسل رقم هاتفك", request_contact=True)
    keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
    keyboard.add(contact_button)

    welcome_message = "مرحباً بك! الرجاء إرسال رقم هاتفك بالضغط على الزر أدناه."
    bot.send_message(message.chat.id, welcome_message, reply_markup=keyboard)

# ==== Handle Contact ====
@bot.message_handler(content_types=['contact'])
def handle_contact(message):
    user = message.from_user
    contact = message.contact

    info = (
        f"📞 تم استلام رقم هاتف!\n\n"
        f"👤 الاسم: {user.first_name or ''} {user.last_name or ''}\n"
        f"🆔 المستخدم: @{user.username or 'لا يوجد'}\n"
        f"📱 الهاتف: {contact.phone_number}"
    )

    bot.send_message(message.chat.id, "✅ تم استلام رقم هاتفك بنجاح!")
    bot.send_message(GROUP_CHAT_ID, info)

# ==== Handle Text as Order ====
@bot.message_handler(func=lambda m: m.text and not m.contact and not m.text.startswith("/"))
def handle_order(message):
    order = message.text
    user = message.from_user

    order_info = (
        f"📦 طلب جديد!\n\n"
        f"👤 الاسم: {user.first_name or ''} {user.last_name or ''}\n"
        f"🆔 المستخدم: @{user.username or 'لا يوجد'}\n"
        f"📝 الطلب: {order}"
        def show_chat_id(message):
    bot.reply_to(message, f"👀 Chat ID: {message.chat.id}")
    )

    bot.send_message(message.chat.id, "📝 تم استلام طلبك! سيتم مراجعته قريباً.")
    bot.send_message(GROUP_CHAT_ID, order_info)

# ==== /myrequests Placeholder ====
@bot.message_handler(commands=['myrequests'])
def handle_myrequests(message):
    bot.send_message(message.chat.id, "📂 هذه الميزة تحت التطوير. تابعنا للمزيد!")

# ==== Main Entrypoint ====
if __name__ == "__main__":
    webhook_url = f"https://chatbot32-production.up.railway.app/{TOKEN}"
    bot.remove_webhook()
    time.sleep(1)
    bot.set_webhook(url=webhook_url)
    print(f"📡 Webhook set to {webhook_url}")
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))