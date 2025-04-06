import os
import logging
from dotenv import load_dotenv
from telegram import Update, ReplyKeyboardMarkup, KeyboardButton
from telegram.ext import (
    Application, CommandHandler, MessageHandler, ContextTypes,
    filters, CallbackContext
)

# Load .env vars
load_dotenv()
TOKEN = os.getenv("TOKEN")
GROUP_CHAT_ID = os.getenv("GROUP_CHAT_ID")

if not TOKEN or not GROUP_CHAT_ID:
    raise ValueError("TOKEN or GROUP_CHAT_ID not set, you magnificent twat.")

# Set up logging
logging.basicConfig(level=logging.INFO)

# Dictionary to store user data
user_data = {}

# Command: /start
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    button = KeyboardButton("📱 أرسل رقم هاتفك", request_contact=True)
    markup = ReplyKeyboardMarkup([[button]], one_time_keyboard=True, resize_keyboard=True)
    await update.message.reply_text("مرحباً! الرجاء إرسال رقم هاتفك للمتابعة.", reply_markup=markup)

# Contact handler
async def handle_contact(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    contact = update.message.contact.phone_number
    user_data[user.id] = {"phone": contact, "orders": []}
    await update.message.reply_text(f"📞 تم استلام رقم هاتفك: {contact}\nأرسل الآن نوع الأسمنت والكمية المطلوبة.")

# Message handler (order)
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    if user.id not in user_data or "phone" not in user_data[user.id]:
        await update.message.reply_text("يرجى إرسال رقم هاتفك أولاً.")
        return

    order = update.message.text
    user_data[user.id]["orders"].append(order)
    phone = user_data[user.id]["phone"]
    message = f"طلب جديد:\n📞 {phone}\n📦 {order}"

    # Send to group
    await context.bot.send_message(chat_id=GROUP_CHAT_ID, text=message)
    await update.message.reply_text("✅ تم استلام طلبك بنجاح، سيتم التواصل معك قريباً.")

# /myrequests command
async def my_requests(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    if user.id not in user_data or not user_data[user.id]["orders"]:
        await update.message.reply_text("لا توجد طلبات محفوظة لك.")
        return

    orders = "\n".join(f"- {o}" for o in user_data[user.id]["orders"])
    await update.message.reply_text(f"🗂 طلباتك السابقة:\n{orders}")

# Set up app
app = Application.builder().token(TOKEN).build()

# Register handlers
app.add_handler(CommandHandler("start", start))
app.add_handler(CommandHandler("myrequests", my_requests))
app.add_handler(MessageHandler(filters.CONTACT, handle_contact))
app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

# Run the bot
if __name__ == "__main__":
    print("🤖 Bot is alive and kicking.")
    app.run_polling()




