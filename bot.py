import os
import logging
import openai
from fastapi import FastAPI, Request
from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    filters,
)

# =========================
# ЛОГИ
# =========================
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)

# =========================
# ПЕРЕМЕННЫЕ ОКРУЖЕНИЯ
# =========================
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

if not TELEGRAM_TOKEN:
    raise ValueError("TELEGRAM_TOKEN не установлен")

if not OPENAI_API_KEY:
    raise ValueError("OPENAI_API_KEY не установлен")

openai.api_key = OPENAI_API_KEY

# =========================
# TELEGRAM APPLICATION
# =========================
application = Application.builder().token(TELEGRAM_TOKEN).build()

# =========================
# ФУНКЦИИ БОТА
# =========================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Привет! Я бот на базе OpenAI. Напиши что-нибудь."
    )

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Отправь любое сообщение, и я отвечу."
    )

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_text = update.message.text

    try:
        response = openai.ChatCompletion.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": user_text}],
            temperature=0.7,
            max_tokens=500,
        )

        answer = response.choices[0].message.content.strip()

    except Exception as e:
        logger.error(f"OpenAI API error: {e}")
        answer = "Произошла ошибка при обращении к серверу."

    await update.message.reply_text(answer)

async def unknown(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Неизвестная команда.")

# =========================
# РЕГИСТРАЦИЯ ХЕНДЛЕРОВ
# =========================
application.add_handler(CommandHandler("start", start))
application.add_handler(CommandHandler("help", help_command))
application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
application.add_handler(MessageHandler(filters.COMMAND, unknown))

# =========================
# FASTAPI
# =========================
app = FastAPI()

@app.on_event("startup")
async def on_startup():
    await application.initialize()
    await application.start()

    webhook_url = f"https://{os.environ['RENDER_EXTERNAL_HOSTNAME']}/webhook"
    await application.bot.set_webhook(webhook_url)

    logger.info(f"Webhook установлен: {webhook_url}")

@app.post("/webhook")
async def telegram_webhook(request: Request):
    data = await request.json()
    update = Update.de_json(data, application.bot)
    await application.process_update(update)
    return {"status": "ok"}

@app.get("/")
async def root():
    return {"status": "Bot is running"}
