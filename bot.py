# bot.py
#TOKEN = "8777038264:AAGr6TwS2mXccJqE-bI2QTGJ-QAGmw_pNbA"

import random, sqlite3, threading, os
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder, CommandHandler, CallbackQueryHandler,
    MessageHandler, filters, ContextTypes
)
from utils import get_solo_number, update_points, start_xo_game

TOKEN = os.environ.get("8777038264:AAGr6TwS2mXccJqE-bI2QTGJ-QAGmw_pNbA")

# ===== DB =====
DB = "db.sqlite"
conn = sqlite3.connect(DB, check_same_thread=False)
cursor = conn.cursor()

# إنشاء الجداول إذا لم تكن موجودة
cursor.execute("""CREATE TABLE IF NOT EXISTS users(user_id INTEGER PRIMARY KEY, points INTEGER DEFAULT 0)""")
cursor.execute("""CREATE TABLE IF NOT EXISTS inventory(user_id INTEGER, item TEXT, quantity INTEGER DEFAULT 1)""")
cursor.execute("""
CREATE TABLE IF NOT EXISTS active_games(
    game_id INTEGER PRIMARY KEY AUTOINCREMENT,
    type TEXT,
    player1 INTEGER,
    player2 INTEGER,
    number INTEGER,
    turn INTEGER,
    tries INTEGER
)
""")
cursor.execute("""
CREATE TABLE IF NOT EXISTS xo_games(
    game_id INTEGER PRIMARY KEY AUTOINCREMENT,
    player1 INTEGER,
    player2 INTEGER,
    board TEXT,
    turn INTEGER,
    winner INTEGER
)
""")
conn.commit()

# ===== Data =====
solo_games = {}
quiz_games = {}
pending_invites = {}

# ===== Menu =====
def menu():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🎮 Solo Guess", callback_data="solo")],
        [InlineKeyboardButton("👥 Challenge", callback_data="invite")],
        [InlineKeyboardButton("🧠 Quiz", callback_data="quiz")],
        [InlineKeyboardButton("💰 Points", callback_data="points")],
        [InlineKeyboardButton("🥇 Leaderboard", callback_data="leader")]
    ])

# ===== Start =====
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    cursor.execute("INSERT OR IGNORE INTO users(user_id) VALUES (?)", (uid,))
    conn.commit()
    await update.message.reply_text("🔥 مرحبا بك في SuperGameBot PRO", reply_markup=menu())

# ===== Buttons =====
async def buttons(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    uid = q.from_user.id
    await q.answer()

    if q.data == "solo":
        number = get_solo_number()
        solo_games[uid] = {"number": number, "tries": 5}
        await q.message.reply_text("🎮 خمن رقم بين 1 و 100 (5 محاولات)")
    elif q.data == "invite":
        await q.message.reply_text("📩 استعمل: /challenge ID")
    elif q.data == "quiz":
        question, answer = random.choice([("عاصمة فرنسا؟","paris"),("5+7=?","12"),("لون السماء؟","blue")])
        quiz_games[uid] = (question, answer)
        await q.message.reply_text(f"🧠 {question}")
    elif q.data == "points":
        cursor.execute("SELECT points FROM users WHERE user_id=?", (uid,))
        pts = cursor.fetchone()[0]
        await q.message.reply_text(f"💰 نقاطك: {pts}")
    elif q.data == "leader":
        cursor.execute("SELECT user_id, points FROM users ORDER BY points DESC LIMIT 10")
        top = cursor.fetchall()
        txt = "🥇 Leaderboard:\n"
        for i, u in enumerate(top, 1):
            txt += f"{i}. {u[0]} - {u[1]} pts\n"
        await q.message.reply_text(txt)

# ===== Guess Handler =====
async def guess(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    txt = update.message.text.lower()

    # SOLO
    if uid in solo_games:
        try:
            g = int(txt)
        except:
            await update.message.reply_text("❌ دخل رقم صحيح")
            return
        game = solo_games[uid]
        game["tries"] -= 1
        if g == game["number"]:
            update_points(uid, 10)
            await update.message.reply_text("🎉 صح! +10 نقاط")
            del solo_games[uid]
        elif game["tries"] <= 0:
            await update.message.reply_text(f"❌ خسرت! الرقم كان {game['number']}")
            del solo_games[uid]
        elif g < game["number"]:
            await update.message.reply_text(f"📉 أكبر | {game['tries']} محاولات")
        else:
            await update.message.reply_text(f"📈 أصغر | {game['tries']} محاولات")
        return

    # QUIZ
    if uid in quiz_games:
        q,a = quiz_games[uid]
        if txt == a:
            update_points(uid, 5)
            await update.message.reply_text("✅ صحيح +5 نقاط")
        else:
            await update.message.reply_text("❌ خطأ")
        del quiz_games[uid]
        return

# ===== Main =====
def main():
    app = ApplicationBuilder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(buttons))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, guess))

    print("🔥 SuperGameBot RUNNING")
    app.run_polling()

if __name__ == "__main__":
    main()
