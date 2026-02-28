import os
import sqlite3
from telegram import Update
from telegram.ext import ApplicationBuilder, MessageHandler, ContextTypes, filters
from openai import OpenAI

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

client = OpenAI(api_key=OPENAI_API_KEY)

conn = sqlite3.connect("memory.db", check_same_thread=False)
cursor = conn.cursor()

cursor.execute("""
CREATE TABLE IF NOT EXISTS messages (
    user_id INTEGER,
    text TEXT
)
""")
conn.commit()

MAX_MEMORY = 100
CONTEXT_LIMIT = 10


def save_message(user_id, text):
    cursor.execute("INSERT INTO messages (user_id, text) VALUES (?, ?)", (user_id, text))
    conn.commit()

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
        SELECT text FROM messages
        WHERE user_id = ?
        ORDER BY rowid DESC
        LIMIT ?
    """, (user_id, CONTEXT_LIMIT))

    rows = cursor.fetchall()
    return [r[0] for r in reversed(rows)]


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    user_text = update.message.text

    save_message(user_id, user_text)

    history = get_context(user_id)

    messages = [{"role": "system", "content": "Ты дружелюбный Telegram бот."}]
    for msg in history:
        messages.append({"role": "user", "content": msg})

    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=messages,
        temperature=0.8
    )

    reply = response.choices[0].message.content
    await update.message.reply_text(reply)


app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()
app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

print("Bot started...")
app.run_polling()
