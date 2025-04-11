import os
import time
import logging
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
recent_updates = set()
user_data = {}

# === Health check ===
@app.route("/", methods=["GET"])
def health_check():
    return "Bot is alive and sexy!", 200

# === Keep-alive Ping ===
def keep_alive():
    while True:
        try:
            requests.get("https://chatbot32-production.up.railway.app/")
        except Exception as e:
            logging.warning("Keep-alive error: %s", e)
        time.sleep(300)

threading.Thread(target=keep_alive, daemon=True).start()

# === Webhook Route ===
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

# === /start Command ===
@bot.message_handler(commands=['start'])
def handle_start(message):
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
    button = types.KeyboardButton("\ud83d\udcf1 \u0623\u0631\u0633\u0644 \u0631\u0642\u0645 \u0647\u0627\u062a\u0641\u0643", request_contact=True)
    markup.add(button)
    bot.send_message(
        message.chat.id,
        "\u0645\u0631\u062d\u0628\u0627\u064b! \u0627\u0644\u0631\u062c\u0627\u0621 \u0625\u0631\u0633\u0627\u0644 \u0631\u0642\u0645 \u0647\u0627\u062a\u0641\u0643 \u0628\u0627\u0644\u0636\u063a\u0637 \u0639\u0644\u0649 \u0627\u0644\u0632\u0631 \u0623\u062f\u0646\u0627\u0647 \u0644\u0644\u0645\u062a\u0627\u0628\u0639\u0629.",
        reply_markup=markup
    )

# === Handle Contact ===
@bot.message_handler(content_types=['contact'])
def handle_contact(message):
    phone = message.contact.phone_number
    user_data[message.chat.id] = {"phone": phone}
    bot.send_message(
        message.chat.id,
        f"\ud83d\udcfe \u062a\u0645 \u0627\u0633\u062a\u0644\u0627\u0645 \u0631\u0642\u0645 \u0647\u0627\u062a\u0641\u0643 \u0628\u0646\u062c\u0627\u062d: {phone}\n\u0623\u0631\u0633\u0644 \u0627\u0644\u0622\u0646 \u0646\u0648\u0639 \u0627\u0644\u0623\u0633\u0645\u0646\u062a \u0648\u0627\u0644\u0643\u0645\u064a\u0629 \u0627\u0644\u0645\u0637\u0644\u0648\u0628\u0629."
    )

# === Spam Keywords ===
SPAM_KEYWORDS = ["vpn", "@speeeedvpnbot", "7 \u0434\u043d\u0435\u0439", "\u043f\u043e\u0434\u0434\u0435\u0440\u0436\u0438\u0432\u0430\u044e\u0442\u0441\u044f", "\ud83d\udd25", "\u0431\u0435\u0441\u043f\u043b\u0430\u0442\u043d\u043e"]

def is_spam(text):
    return any(kw in text.lower() for kw in SPAM_KEYWORDS)

# === Handle Orders ===
@bot.message_handler(func=lambda m: m.text and not m.text.startswith("/"))
def handle_order(message):
    user_id = message.chat.id
    user = message.from_user
    text = message.text

    if user.is_bot:
        logging.info(f"\ud83e\udd16 Ignored message from bot user: {user_id}")
        return

    if is_spam(text):
        logging.warning("\u26a0\ufe0f Ignored suspected spam from %s: %s", user_id, text)
        return

    phone = user_data.get(user_id, {}).get("phone")
    if not phone:
        logging.info(f"\u26d4\ufe0f Ignored message from {user_id} \u2014 no phone on record.")
        return

    msg = (
        f"\ud83d\udce6 \u0637\u0644\u0628 \u062c\u062f\u064a\u062f:\n"
        f"\ud83d\udc64 \u0627\u0644\u0627\u0633\u0645: {user.first_name or ''} {user.last_name or ''}\n"
        f"\ud83c\udd94 \u0627\u0644\u0645\u0633\u062a\u062e\u062f\u0645: @{user.username or 'لا يوجد'}\n"
        f"\ud83d\udcf1 \u0627\u0644\u0647\u0627\u062a\u0641: {phone}\n"
        f"\ud83d\udcdc \u0627\u0644\u0637\u0644\u0628: {text}"
    )

    bot.send_message(GROUP_CHAT_ID, msg)
    bot.send_message(user_id, "\u2705 \u062a\u0645 \u0627\u0633\u062a\u0644\u0627\u0645 \u0637\u0644\u0628\u0643 \u0628\u0646\u062c\u0627\u062d\u060c \u0633\u064a\u062a\u0645 \u0627\u0644\u062a\u0648\u0627\u0635\u0644 \u0645\u0639\u0643 \u0642\u0631\u064a\u0628\u0627ً.")

# === My Requests Placeholder ===
@bot.message_handler(commands=["myrequests"])
def handle_myrequests(message):
    bot.send_message(message.chat.id, "\ud83d\udcc2 \u0647\u0630\u0647 \u0627\u0644\u0645\u064a\u0632\u0629 \u062a\u062d\u062a \u0627\u0644\u062a\u0637\u0648\u064a\u0631 \u062d\u0627\u0644\u064a\u0627ً\u060c \u062a\u0627\u0628\u0639\u0646\u0627 \u0644\u0644\u0645\u0632\u064a\u062f!")

# === Start the App ===
if __name__ == "__main__":
    webhook_url = f"https://chatbot32-production.up.railway.app/{TOKEN}"
    bot.remove_webhook()
    time.sleep(1)
    bot.set_webhook(url=webhook_url)
    logging.info(f"\ud83d\udce1 Webhook set to {webhook_url}")

    logging.info(f"\ud83d\ude80 Starting Flask app on port {PORT}")
    app.run(host="0.0.0.0", port=PORT)
