# bot.py
#TOKEN = "8777038264:AAGr6TwS2mXccJqE-bI2QTGJ-QAGmw_pNbA"
import os
import random
import sqlite3
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, CallbackQueryHandler, MessageHandler, filters, ContextTypes

TOKEN = os.environ.get("8777038264:AAGr6TwS2mXccJqE-bI2QTGJ-QAGmw_pNbA")  # ضع التوكن في Environment Variables

DB = os.path.join(os.path.dirname(__file__), "db.sqlite")
conn = sqlite3.connect(DB, check_same_thread=False)
cursor = conn.cursor()

# إنشاء الجدول إذا لم يكن موجودًا
cursor.execute("""
CREATE TABLE IF NOT EXISTS users (
    user_id INTEGER PRIMARY KEY,
    points INTEGER DEFAULT 0
)
""")
conn.commit()

solo_games = {}
pending_invites = {}
active_games = {}
quiz_games = {}

def menu():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🎮 لعب عادي", callback_data="solo")],
        [InlineKeyboardButton("👥 تحدي لاعب", callback_data="invite")],
        [InlineKeyboardButton("🧠 Quiz", callback_data="quiz")],
        [InlineKeyboardButton("🏆 نقاطي", callback_data="points")],
        [InlineKeyboardButton("🥇 الترتيب", callback_data="leader")]
    ])

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    cursor.execute("INSERT OR IGNORE INTO users(user_id) VALUES (?)", (uid,))
    conn.commit()
    await update.message.reply_text("🔥 مرحبا بك في GAME BOT PRO", reply_markup=menu())

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
    elif q.data == "quiz":
        question = random.choice([
            ("عاصمة فرنسا؟", "paris"),
            ("5+7=?", "12"),
            ("لون السماء؟", "blue")
        ])
        quiz_games[uid] = question
        await q.message.reply_text(f"🧠 {question[0]}")
    elif q.data == "points":
        cursor.execute("SELECT points FROM users WHERE user_id=?", (uid,))
        pts = cursor.fetchone()[0]
        await q.message.reply_text(f"🏆 نقاطك: {pts}")
    elif q.data == "leader":
        cursor.execute("SELECT user_id, points FROM users ORDER BY points DESC LIMIT 5")
        top = cursor.fetchall()
        txt = "🥇 الترتيب:\n"
        for i, u in enumerate(top, 1):
            txt += f"{i}. {u[0]} - {u[1]} pts\n"
        await q.message.reply_text(txt)

async def solo_guess(uid, text, update):
    game = solo_games[uid]
    game["tries"] -= 1
    try:
        g = int(text)
    except:
        await update.message.reply_text("❌ دخل رقم صحيح")
        return
    if g == game["number"]:
        cursor.execute("UPDATE users SET points = points + 10 WHERE user_id=?", (uid,))
        conn.commit()
        await update.message.reply_text("🎉 ربحت +10 نقاط")
        del solo_games[uid]
    elif game["tries"] <= 0:
        await update.message.reply_text(f"❌ خسرت! الرقم {game['number']}")
        del solo_games[uid]
    elif g < game["number"]:
        await update.message.reply_text(f"📉 أكبر | {game['tries']} محاولات")
    else:
        await update.message.reply_text(f"📈 أصغر | {game['tries']} محاولات")

async def guess(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    txt = update.message.text.lower()
    if uid in solo_games:
        await solo_guess(uid, txt, update)
        return
    if uid in quiz_games:
        q, ans = quiz_games[uid]
        if txt == ans:
            cursor.execute("UPDATE users SET points = points + 5 WHERE user_id=?", (uid,))
            conn.commit()
            await update.message.reply_text("✅ صحيح +5 نقاط")
        else:
            await update.message.reply_text("❌ خطأ")
        del quiz_games[uid]
        return

def main():
    app = ApplicationBuilder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(buttons))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, guess))
    print("🔥 SuperGameBot RUNNING")
    app.run_polling()

if __name__ == "__main__":
    main()
