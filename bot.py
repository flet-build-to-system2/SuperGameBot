import random
import sqlite3
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, CallbackQueryHandler, MessageHandler, filters, ContextTypes
from utils import draw_board, check_xo_win, buy_item, format_leaderboard

# استبدل هذا التوكن بتوكن جديد للأمان
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
cursor.execute("""
CREATE TABLE IF NOT EXISTS inventory (
    user_id INTEGER,
    item TEXT
)
""")
conn.commit()

# ===== Data =====
solo_games = {}
quiz_games = {}
pending_challenges = {}
active_guess_games = {}
pending_xo = {}
active_xo_games = {}

# ===== Menu =====
def menu():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🎮 Solo Game", callback_data="solo")],
        [InlineKeyboardButton("👥 Challenge Guess", callback_data="challenge")],
        [InlineKeyboardButton("❌⭕ XO", callback_data="xo")],
        [InlineKeyboardButton("🧠 Quiz", callback_data="quiz")],
        [InlineKeyboardButton("💰 متجر", callback_data="shop")],
        [InlineKeyboardButton("🏆 نقاطي", callback_data="points")],
        [InlineKeyboardButton("🥇 Leaderboard", callback_data="leader")]
    ])

# ===== Start =====
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    cursor.execute("INSERT OR IGNORE INTO users(user_id) VALUES (?)", (uid,))
    conn.commit()
    await update.message.reply_text("🔥 مرحبا بك في SuperGameBot PRO", reply_markup=menu())

# ===== Buttons Handler (للأزرار العامة) =====
async def buttons(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    uid = q.from_user.id
    await q.answer()

    if q.data == "solo":
        number = random.randint(1, 100)
        solo_games[uid] = {"number": number, "tries": 5}
        await q.message.reply_text("🎮 خمن رقم بين 1 و 100 (5 محاولات)")

    elif q.data == "quiz":
        question = random.choice([("عاصمة فرنسا؟", "paris"), ("5+7=?", "12"), ("لون السماء؟", "blue")])
        quiz_games[uid] = question
        await q.message.reply_text(f"🧠 {question[0]}")

    elif q.data == "challenge":
        await q.message.reply_text("📩 استعمل: /challenge UID")

    elif q.data == "xo":
        await q.message.reply_text("📩 استعمل: /xo UID لتحدي صديق")

    elif q.data == "shop":
        kb = [
            [InlineKeyboardButton("🎟️ محاولة إضافية (20 pts)", callback_data="buy_try")],
            [InlineKeyboardButton("💡 تلميح (15 pts)", callback_data="buy_hint")]
        ]
        await q.message.reply_text("🛒 المتجر:", reply_markup=InlineKeyboardMarkup(kb))

    elif q.data == "points":
        cursor.execute("SELECT points FROM users WHERE user_id=?", (uid,))
        pts = cursor.fetchone()[0]
        await q.message.reply_text(f"🏆 نقاطك: {pts}")

    elif q.data == "leader":
        txt = format_leaderboard(cursor)
        await q.message.reply_text(txt)

    elif q.data == "buy_try":
        success = buy_item(cursor, conn, uid, "try", 20)
        await q.message.reply_text("✅ شريت محاولة إضافية" if success else "❌ نقاطك ناقصة")

    elif q.data == "buy_hint":
        success = buy_item(cursor, conn, uid, "hint", 15)
        await q.message.reply_text("✅ شريت تلميح" if success else "❌ نقاطك ناقصة")

# ===== Commands =====
async def challenge_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    if not context.args:
        await update.message.reply_text("استعمل: /challenge UID")
        return
    try:
        opponent = int(context.args[0])
        pending_challenges[opponent] = uid
        kb = [[
            InlineKeyboardButton("✅ قبول", callback_data=f"guess_acc_{uid}"),
            InlineKeyboardButton("❌ رفض", callback_data=f"guess_rej_{uid}")
        ]]
        await context.bot.send_message(opponent, f"👥 تحدي Guess Game من {uid}!", reply_markup=InlineKeyboardMarkup(kb))
        await update.message.reply_text("📨 تم إرسال طلب التحدي")
    except:
        await update.message.reply_text("❌ تأكد من الـ ID أو أن اللاعب بدأ البوت")

async def xo_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    if not context.args:
        await update.message.reply_text("استعمل: /xo UID")
        return
    try:
        opponent = int(context.args[0])
        pending_xo[opponent] = uid
        kb = [[
            InlineKeyboardButton("✅ قبول", callback_data=f"xo_acc_{uid}"),
            InlineKeyboardButton("❌ رفض", callback_data=f"xo_rej_{uid}")
        ]]
        await context.bot.send_message(opponent, f"❌⭕ تحدي XO من {uid}!", reply_markup=InlineKeyboardMarkup(kb))
        await update.message.reply_text("📨 تم إرسال طلب التحدي")
    except:
        await update.message.reply_text("❌ تأكد من الـ ID أو أن اللاعب بدأ البوت")

# ===== Accept/Reject Handlers =====
async def handle_guess_invite(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    uid = q.from_user.id
    await q.answer()
    challenger = int(q.data.split("_")[2])
    
    if q.data.startswith("guess_acc"):
        number = random.randint(1, 100)
        active_guess_games[uid] = {"op": challenger, "number": number, "turn": challenger, "tries": 5}
        active_guess_games[challenger] = {"op": uid, "number": number, "turn": challenger, "tries": 5}
        await context.bot.send_message(challenger, "🔥 خصمك قبل التحدي! ابدأ بالتخمين، دورك الآن.")
        await q.edit_message_text("✅ بدأت اللعبة! انتظر دور الخصم.")
    else:
        await context.bot.send_message(challenger, "❌ تم رفض طلب التحدي.")
        await q.edit_message_text("❌ رفضت التحدي.")

async def handle_xo_invite(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    uid = q.from_user.id
    await q.answer()
    challenger = int(q.data.split("_")[2])
    
    if q.data.startswith("xo_acc"):
        board = [" "] * 9
        active_xo_games[uid] = {"p1": challenger, "p2": uid, "board": board, "turn": challenger}
        active_xo_games[challenger] = {"p1": challenger, "p2": uid, "board": board, "turn": challenger}
        await context.bot.send_message(challenger, draw_board(board) + "\n🔥 خصمك قبل! دورك الآن (X)")
        await q.edit_message_text("✅ بدأت XO! انتظر الخصم (O)")
    else:
        await context.bot.send_message(challenger, "❌ تم رفض طلب XO.")
        await q.edit_message_text("❌ رفضت التحدي.")

# ===== Message Handler (نفس المنطق السابق) =====
async def guess(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    txt = update.message.text.lower()

    # --- Solo ---
    if uid in solo_games:
        try: g = int(txt)
        except: await update.message.reply_text("❌ دخل رقم صالح"); return
        game = solo_games[uid]; game["tries"]-=1
        if g==game["number"]:
            cursor.execute("UPDATE users SET points=points+10 WHERE user_id=?", (uid,))
            conn.commit()
            await update.message.reply_text("🎉 ربحت +10 نقاط")
            del solo_games[uid]
        elif game["tries"]<=0:
            await update.message.reply_text(f"❌ خسرت! الرقم كان {game['number']}")
            del solo_games[uid]
        elif g<game["number"]:
            await update.message.reply_text(f"📉 أكبر | {game['tries']} محاولات متبقية")
        else:
            await update.message.reply_text(f"📈 أصغر | {game['tries']} محاولات متبقية")
        return

    # --- Quiz ---
    if uid in quiz_games:
        q, ans = quiz_games[uid]
        if txt==ans:
            cursor.execute("UPDATE users SET points=points+5 WHERE user_id=?", (uid,))
            conn.commit()
            await update.message.reply_text("✅ صحيح +5 نقاط")
        else: await update.message.reply_text("❌ خطأ")
        del quiz_games[uid]; return

    # --- Multiplayer Guess ---
    if uid in active_guess_games:
        game = active_guess_games[uid]
        if game["turn"]!=uid:
            await update.message.reply_text("⏳ ماشي دورك")
            return
        try: g = int(txt)
        except: return
        game["tries"]-=1; op = game["op"]
        if g==game["number"]:
            cursor.execute("UPDATE users SET points=points+30 WHERE user_id=?", (uid,))
            conn.commit()
            await update.message.reply_text("🏆 ربحت +30")
            await context.bot.send_message(op, "❌ خسرت، الخصم وجد الرقم!")
            del active_guess_games[uid]; del active_guess_games[op]
        elif game["tries"]<=0:
            await update.message.reply_text("❌ خسرت، انتهت المحاولات!")
            await context.bot.send_message(op, "🏆 ربحت! الخصم استنفد محاولاته")
            del active_guess_games[uid]; del active_guess_games[op]
        else:
            hint = "📉 الخصم يحتاج رقم أكبر" if g<game["number"] else "📈 الخصم يحتاج رقم أصغر"
            await update.message.reply_text(f"نصيحة لخصمك: {hint}")
            game["turn"]=op; active_guess_games[op]["turn"]=op
            await context.bot.send_message(op, f"🎯 دورك! الخصم خمن {g} وكان خطأ. حاول الآن.")
        return

    # --- Multiplayer XO ---
    if uid in active_xo_games:
        game = active_xo_games[uid]
        if game["turn"]!=uid:
            await update.message.reply_text("⏳ ماشي دورك")
            return
        board = game["board"]
        try:
            pos=int(txt)
            if pos < 0 or pos > 8 or board[pos]!=" ": raise ValueError
        except:
            await update.message.reply_text("❌ اكتب رقم متاح من 0-8"); return
        
        board[pos]="X" if uid==game["p1"] else "O"
        winner=check_xo_win(board)
        if winner:
            if winner in ["X", "O"]:
                cursor.execute("UPDATE users SET points=points+20 WHERE user_id=?", (uid,))
                conn.commit()
                msg = draw_board(board)+f"\n🎉 فزت بالمباراة! +20 نقطة"
                await update.message.reply_text(msg)
                await context.bot.send_message(game["p2"] if uid==game["p1"] else game["p1"], draw_board(board)+"\n❌ خسرت!")
            else:
                await update.message.reply_text(draw_board(board)+"\n🤝 تعادل!")
            del active_xo_games[game["p1"]]; del active_xo_games[game["p2"]]
            return
            
        next_turn = game["p2"] if uid==game["p1"] else game["p1"]
        game["turn"]=next_turn
        active_xo_games[next_turn]["turn"]=next_turn
        await context.bot.send_message(next_turn, draw_board(board)+"\n🔥 دورك الآن")
        await update.message.reply_text("تم، انتظر دور الخصم...")
        return

# ===== Main =====
def main():
    app = ApplicationBuilder().token(TOKEN).build()

    # الترتيب هنا هو السر!
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("challenge", challenge_cmd))
    app.add_handler(CommandHandler("xo", xo_cmd))

    # 1. معالجات طلبات التحدي (التي تحتوي على Pattern) أولاً
    app.add_handler(CallbackQueryHandler(handle_guess_invite, pattern="^guess_"))
    app.add_handler(CallbackQueryHandler(handle_xo_invite, pattern="^xo_"))

    # 2. معالج الأزرار العام ثانياً
    app.add_handler(CallbackQueryHandler(buttons))

    # 3. معالج الرسائل النصية
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, guess))

    print("🔥 SuperGameBot PRO RUNNING")
    app.run_polling()

if __name__ == "__main__":
    main()
