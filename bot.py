# bot.py
import random, sqlite3
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, CallbackQueryHandler, MessageHandler, filters, ContextTypes
from utils import draw_board, check_xo_win, buy_item, format_leaderboard

TOKEN = "8777038264:AAGr6TwS2mXccJqE-bI2QTGJ-QAGmw_pNbA"

# ===== DB =====
conn = sqlite3.connect("db.sqlite", check_same_thread=False)
cursor = conn.cursor()

# إنشاء الجداول إذا ما كايناش
cursor.execute("""
CREATE TABLE IF NOT EXISTS users (
    user_id INTEGER PRIMARY KEY,
    points INTEGER DEFAULT 0
)
""")
cursor.execute("""
CREATE TABLE IF NOT EXISTS inventory (
    user_id INTEGER,
    item TEXT
)
""")
cursor.execute("""
CREATE TABLE IF NOT EXISTS xo_games (
    game_id INTEGER PRIMARY KEY AUTOINCREMENT,
    player1 INTEGER,
    player2 INTEGER,
    board TEXT,
    turn TEXT
)
""")
conn.commit()

# ===== Data =====
solo_games = {}
quiz_games = {}
xo_games_active = {}

# ===== Menu =====
def menu():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🎮 Solo Game", callback_data="solo")],
        [InlineKeyboardButton("🧠 Quiz", callback_data="quiz")],
        [InlineKeyboardButton("❌⭕ XO", callback_data="xo")],
        [InlineKeyboardButton("💰 متجر", callback_data="shop")],
        [InlineKeyboardButton("🏆 نقاطي", callback_data="points")],
        [InlineKeyboardButton("🥇 Leaderboard", callback_data="leader")]
    ])

# ===== Start =====
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    try:
        cursor.execute("INSERT OR IGNORE INTO users(user_id) VALUES (?)", (uid,))
        conn.commit()
    except sqlite3.DatabaseError as e:
        print("DB Error:", e)
    await update.message.reply_text("🔥 مرحبا بك في SuperGameBot", reply_markup=menu())

# ===== Buttons =====
async def buttons(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    uid = q.from_user.id
    await q.answer()

    # Solo Game
    if q.data == "solo":
        number = random.randint(1, 100)
        solo_games[uid] = {"number": number, "tries":5}
        await q.message.reply_text("🎮 خمن رقم بين 1 و 100 (5 محاولات)")

    # Quiz
    elif q.data == "quiz":
        question = random.choice([
            ("عاصمة فرنسا؟","paris"),
            ("5+7=?","12"),
            ("لون السماء؟","blue")
        ])
        quiz_games[uid] = question
        await q.message.reply_text(f"🧠 {question[0]}")

    # XO Game (Single Player vs Bot)
    elif q.data == "xo":
        board = [" "]*9
        xo_games_active[uid] = {"board":board, "turn":"X"} # المستخدم يبدأ X
        await q.message.reply_text(draw_board(board) + "\n📝 اكتب رقم المربع 0-8 للعب.")

    # متجر
    elif q.data == "shop":
        kb = [
            [InlineKeyboardButton("🎟️ محاولة إضافية (20 pts)", callback_data="buy_try")],
            [InlineKeyboardButton("💡 تلميح (15 pts)", callback_data="buy_hint")]
        ]
        await q.message.reply_text("🛒 المتجر:", reply_markup=InlineKeyboardMarkup(kb))

    # نقاط
    elif q.data == "points":
        cursor.execute("SELECT points FROM users WHERE user_id=?", (uid,))
        pts = cursor.fetchone()[0]
        await q.message.reply_text(f"🏆 نقاطك: {pts}")

    # Leaderboard
    elif q.data == "leader":
        txt = format_leaderboard(cursor)
        await q.message.reply_text(txt)

    # شراء متجر
    elif q.data == "buy_try":
        success = buy_item(cursor, conn, uid, "try", 20)
        await q.message.reply_text("✅ شريت محاولة إضافية" if success else "❌ نقاطك ناقصة")
    elif q.data == "buy_hint":
        success = buy_item(cursor, conn, uid, "hint", 15)
        await q.message.reply_text("✅ شريت تلميح" if success else "❌ نقاطك ناقصة")

# ===== Message Handler =====
async def guess(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    txt = update.message.text.lower()

    # --- Solo Game ---
    if uid in solo_games:
        try:
            g = int(txt)
        except:
            await update.message.reply_text("❌ دخل رقم صالح")
            return
        game = solo_games[uid]
        game["tries"] -= 1
        if g == game["number"]:
            cursor.execute("UPDATE users SET points = points + 10 WHERE user_id=?", (uid,))
            conn.commit()
            await update.message.reply_text("🎉 ربحت +10 نقاط")
            del solo_games[uid]
        elif game["tries"] <=0:
            await update.message.reply_text(f"❌ خسرت! الرقم كان {game['number']}")
            del solo_games[uid]
        elif g < game["number"]:
            await update.message.reply_text(f"📉 أكبر | {game['tries']} محاولات متبقية")
        else:
            await update.message.reply_text(f"📈 أصغر | {game['tries']} محاولات متبقية")
        return

    # --- Quiz ---
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

    # --- XO Single Player ---
    if uid in xo_games_active:
        game = xo_games_active[uid]
        board = game["board"]
        try:
            pos = int(txt)
            if board[pos] != " ":
                await update.message.reply_text("❌ المربع مشغول")
                return
        except:
            await update.message.reply_text("❌ اكتب رقم من 0 إلى 8")
            return

        # حركة المستخدم
        board[pos] = "X"
        winner = check_xo_win(board)
        if winner:
            if winner=="X":
                cursor.execute("UPDATE users SET points = points + 10 WHERE user_id=?", (uid,))
                conn.commit()
                await update.message.reply_text(draw_board(board) + "\n🎉 ربحت +10 نقاط")
            elif winner=="Draw":
                await update.message.reply_text(draw_board(board) + "\n🤝 تعادل")
            del xo_games_active[uid]
            return

        # حركة البوت عشوائي
        empty = [i for i,v in enumerate(board) if v==" "]
        if empty:
            bot_pos = random.choice(empty)
            board[bot_pos] = "O"

        winner = check_xo_win(board)
        if winner:
            if winner=="O":
                await update.message.reply_text(draw_board(board) + "\n❌ خسرت ضد البوت")
            elif winner=="Draw":
                await update.message.reply_text(draw_board(board) + "\n🤝 تعادل")
            del xo_games_active[uid]
            return

        await update.message.reply_text(draw_board(board) + "\n📝 دورك، اكتب رقم المربع:")

# ===== Main =====
def main():
    app = ApplicationBuilder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(buttons))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, guess))
    print("🔥 SuperGameBot RUNNING")
    app.run_polling()

if __name__=="__main__":
    main()