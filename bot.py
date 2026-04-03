# bot.py
#TOKEN = "8777038264:AAGr6TwS2mXccJqE-bI2QTGJ-QAGmw_pNbA"
import random
import sqlite3
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder, CommandHandler, CallbackQueryHandler,
    MessageHandler, filters, ContextTypes
)

TOKEN = "8777038264:AAGr6TwS2mXccJqE-bI2QTGJ-QAGmw_pNbA"

# ===== DB =====
conn = sqlite3.connect("db.sqlite", check_same_thread=False)
cursor = conn.cursor()
cursor.execute("""
CREATE TABLE IF NOT EXISTS users (
    user_id INTEGER PRIMARY KEY,
    points INTEGER DEFAULT 0
)
""")
conn.commit()

# ===== Data =====
solo_games = {}
pending_invites = {}
active_games = {}
xo_games = {}

# ===== Menu =====
def menu():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🎮 لعب عادي", callback_data="solo")],
        [InlineKeyboardButton("👥 تحدي لاعب", callback_data="invite")],
        [InlineKeyboardButton("❌ XO", callback_data="xo")],
        [InlineKeyboardButton("🏆 نقاطي", callback_data="points")]
    ])

# ===== Handlers =====
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    cursor.execute("INSERT OR IGNORE INTO users (user_id) VALUES (?)", (uid,))
    conn.commit()
    await update.message.reply_text("🔥 مرحبا بك في SuperGameBot", reply_markup=menu())

async def buttons(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    uid = q.from_user.id
    await q.answer()

    if q.data == "solo":
        number = random.randint(1, 100)
        solo_games[uid] = {"number": number, "tries": 5}
        await q.message.reply_text("🎮 خمن رقم بين 1 و 100 (5 محاولات)")

    elif q.data == "invite":
        await q.message.reply_text("📩 استعمل: /challenge ID")

    elif q.data == "xo":
        await q.message.reply_text("🎲 XO يبدأ قريبا!")

    elif q.data == "points":
        cursor.execute("SELECT points FROM users WHERE user_id=?", (uid,))
        pts = cursor.fetchone()[0]
        await q.message.reply_text(f"🏆 نقاطك: {pts}")

async def guess(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    txt = update.message.text.lower()

    if uid in solo_games:
        game = solo_games[uid]
        try:
            g = int(txt)
        except:
            await update.message.reply_text("❌ أدخل رقم صحيح!")
            return

        game["tries"] -= 1
        if g == game["number"]:
            cursor.execute("UPDATE users SET points = points + 10 WHERE user_id=?", (uid,))
            conn.commit()
            await update.message.reply_text("🎉 ربحت +10 نقاط")
            del solo_games[uid]
        elif game["tries"] <= 0:
            await update.message.reply_text(f"❌ خسرت! الرقم الصحيح: {game['number']}")
            del solo_games[uid]
        elif g < game["number"]:
            await update.message.reply_text(f"📉 أكبر | {game['tries']} محاولات متبقية")
        else:
            await update.message.reply_text(f"📈 أصغر | {game['tries']} محاولات متبقية")

def main():
    app = ApplicationBuilder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(buttons))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, guess))
    print("🔥 Bot is running...")
    app.run_polling()

if __name__ == "__main__":
    main()