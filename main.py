import os
import logging
from dotenv import load_dotenv

from telegram import Update
from telegram.ext import (
    ApplicationBuilder,
    ContextTypes,
    CommandHandler,
    MessageHandler,
    filters,
)

import db
from utils import is_valid_email, get_btc_price

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logging.getLogger("httpx").setLevel(logging.WARNING)

load_dotenv()
TOKEN = os.getenv("BOT_TOKEN")

STATE_WAITING_EMAIL = 'WAITING_EMAIL'
STATE_WAITING_TASK_TITLE = 'WAITING_TASK_TITLE'


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Sends welcome message and resets state."""
    user_id = update.effective_user.id
    await db.set_user_state(user_id, None)
    
    welcome_text = (
        "Welcome to BridgeGPT Test Bot 🤖\n\n"
        "Commands:\n"
        "/register → ثبت ایمیل\n"
        "/addtask → اضافه کردن تسک\n"
        "/tasks → لیست تسک‌ها\n"
        "/btc → قیمت لحظه‌ای بیت‌کوین"
    )
    await update.message.reply_text(welcome_text)

async def cmd_register(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    await db.set_user_state(user_id, STATE_WAITING_EMAIL)
    await update.message.reply_text("Please send your email address:")

async def cmd_addtask(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    await db.set_user_state(user_id, STATE_WAITING_TASK_TITLE)
    await update.message.reply_text("Send your task title:")

async def list_tasks(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id

    await db.set_user_state(user_id, None)
    
    tasks = await db.get_user_tasks(user_id)
    if not tasks:
        await update.message.reply_text("You have no tasks yet.")
    else:
        msg = "Your tasks:\n"
        for idx, title in enumerate(tasks, 1):
            msg += f"{idx}) {title}\n"
        await update.message.reply_text(msg)

async def btc_price_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Fetches BTC price."""
    await context.bot.send_chat_action(chat_id=update.effective_chat.id, action="typing")
    data = await get_btc_price()
    if data:
        msg = f"💰 BTC Price: ${data['price']}\n📅 Last Updated: {data['updated_at']}"
        await update.message.reply_text(msg)
    else:
        await update.message.reply_text("⚠️ Failed to fetch price.")


async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Checks DB state and processes text accordingly."""
    user_id = update.effective_user.id
    text = update.message.text.strip()
    
    state = await db.get_user_state(user_id)
    
    if state == STATE_WAITING_EMAIL:
        if is_valid_email(text):
            await update.message.reply_text("Email saved ✅", quote=True)
            await db.register_user_email(user_id, text)
        else:
            await update.message.reply_text("Invalid email ❌\nPlease try again.", quote=True)
            
    elif state == STATE_WAITING_TASK_TITLE:
        if text:
            await update.message.reply_text("Task saved ✅", quote=True)
            await db.add_task(user_id, text)
        else:
            await update.message.reply_text("Task title cannot be empty.")
            
    else:
        await update.message.reply_text("I didn't understand that command. Try /start for help.")

if __name__ == '__main__':
    if not TOKEN:
        print("Error: BOT_TOKEN is missing in .env file.")
        exit(1)
    
    async def post_init(application):
        await db.init_db()

    application = ApplicationBuilder().token(TOKEN).post_init(post_init).build()

    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("register", cmd_register))
    application.add_handler(CommandHandler("addtask", cmd_addtask))
    application.add_handler(CommandHandler("tasks", list_tasks))
    application.add_handler(CommandHandler("btc", btc_price_handler))

    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))

    print("Bot is running with DB-based state management...")
    application.run_polling()