# bot.py
import random, sqlite3
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, CallbackQueryHandler, MessageHandler, filters, ContextTypes
from utils import draw_board, check_xo_win

TOKEN = "8290038160:AAH4cwCgcDQoqMaI3ff7_FtuHMCZON_TSDA"
conn = sqlite3.connect("db.sqlite", check_same_thread=False)
cursor = conn.cursor()

solo_games = {}
active_games = {}
quiz_games = {}
xo_games = {}

# --- Menu ---
def menu():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🎮 لعب عادي", callback_data="solo")],
        [InlineKeyboardButton("👥 تحدي لاعب", callback_data="invite")],
        [InlineKeyboardButton("🧠 Quiz", callback_data="quiz")],
        [InlineKeyboardButton("❌⭕ XO", callback_data="xo")],
        [InlineKeyboardButton("💰 متجر", callback_data="shop")],
        [InlineKeyboardButton("🏆 نقاطي", callback_data="points")],
        [InlineKeyboardButton("🥇 الترتيب", callback_data="leader")]
    ])

# --- Start ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    cursor.execute("INSERT OR IGNORE INTO users(user_id) VALUES (?)", (uid,))
    conn.commit()
    await update.message.reply_text("🔥 مرحبا بك في SuperGameBot", reply_markup=menu())

# --- Buttons ---
async def buttons(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    uid = q.from_user.id
    await q.answer()

    if q.data == "solo":
        number = random.randint(1,100)
        solo_games[uid] = {"number": number, "tries":5}
        await q.message.reply_text("🎮 خمن رقم بين 1 و 100 (5 محاولات)")

    elif q.data == "quiz":
        question = random.choice([
            ("عاصمة فرنسا؟","paris"),
            ("5+7=?","12"),
            ("لون السماء؟","blue")
        ])
        quiz_games[uid] = question
        await q.message.reply_text(f"🧠 {question[0]}")

    elif q.data == "points":
        cursor.execute("SELECT points FROM users WHERE user_id=?",(uid,))
        pts = cursor.fetchone()[0]
        await q.message.reply_text(f"🏆 نقاطك: {pts}")

    elif q.data == "leader":
        cursor.execute("SELECT user_id, points FROM users ORDER BY points DESC LIMIT 10")
        top = cursor.fetchall()
        txt = "🥇 الترتيب:\n"
        for i,u in enumerate(top,1):
            txt += f"{i}. {u[0]} - {u[1]} pts\n"
        await q.message.reply_text(txt)

# --- Guess Handler ---
async def guess(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    txt = update.message.text.lower()

    # Solo
    if uid in solo_games:
        try:
            g = int(txt)
        except: return
        game = solo_games[uid]
        game["tries"] -=1
        if g==game["number"]:
            cursor.execute("UPDATE users SET points = points +10 WHERE user_id=?",(uid,))
            conn.commit()
            await update.message.reply_text("🎉 ربحت +10 نقاط")
            del solo_games[uid]
        elif game["tries"]<=0:
            await update.message.reply_text(f"❌ خسرت! الرقم {game['number']}")
            del solo_games[uid]
        elif g<game["number"]:
            await update.message.reply_text(f"📉 أكبر | {game['tries']} محاولات")
        else:
            await update.message.reply_text(f"📈 أصغر | {game['tries']} محاولات")
        return

    # Quiz
    if uid in quiz_games:
        q,ans = quiz_games[uid]
        if txt==ans:
            cursor.execute("UPDATE users SET points=points+5 WHERE user_id=?",(uid,))
            conn.commit()
            await update.message.reply_text("✅ صحيح +5 نقاط")
        else:
            await update.message.reply_text("❌ خطأ")
        del quiz_games[uid]
        return

# --- Main ---
def main():
    app = ApplicationBuilder().token(TOKEN).build()
    app.add_handler(CommandHandler("start",start))
    app.add_handler(CallbackQueryHandler(buttons))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND,guess))
    print("🔥 SuperGameBot RUNNING")
    app.run_polling()

if __name__=="__main__":
    main()