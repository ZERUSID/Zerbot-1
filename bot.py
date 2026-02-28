import os
import sqlite3
import logging
from telegram import Update
from telegram.ext import ApplicationBuilder, MessageHandler, ContextTypes, filters
from openai import OpenAI

# ------------------------
# Настройки
# ------------------------

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

if not TELEGRAM_TOKEN:
    raise ValueError("TELEGRAM_TOKEN не установлен")
if not OPENAI_API_KEY:
    raise ValueError("OPENAI_API_KEY не установлен")

client = OpenAI(api_key=OPENAI_API_KEY)

logging.basicConfig(level=logging.INFO)

# ------------------------
# База данных
# ------------------------

conn = sqlite3.connect("memory.db", check_same_thread=False)
cursor = conn.cursor()

cursor.execute("""
CREATE TABLE IF NOT EXISTS messages (
    user_id INTEGER,
    role TEXT,
    text TEXT
)
""")
conn.commit()

MAX_MEMORY = 50
CONTEXT_LIMIT = 10

def save_message(user_id, role, text):
    cursor.execute(
        "INSERT INTO messages (user_id, role, text) VALUES (?, ?, ?)",
        (user_id, role, text)
    )
    conn.commit()

    # ограничение памяти
    cursor.execute("""
        DELETE FROM messages
        WHERE user_id = ?
        AND rowid NOT IN (
            SELECT rowid FROM messages
            WHERE user_id = ?
            ORDER BY rowid DESC
            LIMIT ?
        )
    """, (user_id, user_id, MAX_MEMORY))
    conn.commit()


def get_context(user_id):
    cursor.execute("""
        SELECT role, text FROM messages
        WHERE user_id = ?
        ORDER BY rowid DESC
        LIMIT ?
    """, (user_id, CONTEXT_LIMIT))

    rows = cursor.fetchall()
    rows.reverse()

    messages = []
    for role, text in rows:
        messages.append({"role": role, "content": text})

    return messages

# ------------------------
# Обработка сообщений
# ------------------------

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        user_id = update.message.from_user.id
        user_text = update.message.text

        # сохраняем сообщение пользователя
        save_message(user_id, "user", user_text)

        history = get_context(user_id)

        # добавляем системную роль
        messages = [
            {"role": "system", "content": "Ты дружелюбный Telegram бот. Отвечай кратко и по делу."}
        ] + history

        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=messages,
            temperature=0.7
        )

        reply = response.choices[0].message.content

        # сохраняем ответ бота
        save_message(user_id, "assistant", reply)

        await update.message.reply_text(reply)

    except Exception as e:
        logging.error(f"Ошибка: {e}")
        await update.message.reply_text("Произошла ошибка. Попробуй позже.")

# ------------------------
# Запуск
# ------------------------

def main():
    app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    print("Bot started...")
    app.run_polling()

if __name__ == "__main__":
    main()
