import os
import logging
from fastapi import FastAPI, Request
from telegram import Update, Bot
from telegram.ext import (
    Dispatcher,
    CommandHandler,
    MessageHandler,
    filters,
)
import openai
import uvicorn

# =======================
# Настройки
# =======================
TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY")

if not TELEGRAM_TOKEN:
    raise ValueError("TELEGRAM_TOKEN не установлен")
if not OPENAI_API_KEY:
    raise ValueError("OPENAI_API_KEY не установлен")

openai.api_key = OPENAI_API_KEY

# Логирование
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# =======================
# Инициализация бота
# =======================
bot = Bot(token=TELEGRAM_TOKEN)
dispatcher = Dispatcher(bot, None, workers=0)

# =======================
# Хендлеры
# =======================
def start(update: Update, context):
    update.message.reply_text("Привет! Я готов к работе.")

def echo(update: Update, context):
    """Отвечает через OpenAI на любое сообщение"""
    user_text = update.message.text
    try:
        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=[{"role": "user", "content": user_text}],
            temperature=0.7,
            max_tokens=300,
        )
        reply = response.choices[0].message.content.strip()
    except Exception as e:
        reply = f"Ошибка при обращении к OpenAI: {e}"
    update.message.reply_text(reply)

# Добавляем хендлеры
dispatcher.add_handler(CommandHandler("start", start))
dispatcher.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), echo))

# =======================
# FastAPI
# =======================
app = FastAPI()

@app.post(f"/webhook/{TELEGRAM_TOKEN}")
async def telegram_webhook(req: Request):
    data = await req.json()
    update = Update.de_json(data, bot)
    dispatcher.process_update(update)
    return {"ok": True}

@app.on_event("startup")
async def set_webhook():
    """Устанавливаем webhook при старте сервера"""
    url = f"https://{os.environ.get('RENDER_EXTERNAL_HOSTNAME')}/webhook/{TELEGRAM_TOKEN}"
    logger.info(f"Setting webhook to {url}")
    await bot.set_webhook(url)

# =======================
# Запуск локально (для разработки)
# =======================
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run("bot:app", host="0.0.0.0", port=port, log_level="info")
