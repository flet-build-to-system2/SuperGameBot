# bot.py
import random
import sqlite3
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram import BotCommand
from telegram.ext import ApplicationBuilder, CommandHandler, CallbackQueryHandler, MessageHandler, filters, ContextTypes
from utils import draw_xo_keyboard, check_xo_win, buy_item, format_leaderboard

TOKEN = "8777038264:AAGr6TwS2mXccJqE-bI2QTGJ-QAGmw_pNbA"

# ===== قاعدة البيانات =====
conn = sqlite3.connect("db.sqlite", check_same_thread=False)
cursor = conn.cursor()

cursor.execute("CREATE TABLE IF NOT EXISTS users (user_id INTEGER PRIMARY KEY, points INTEGER DEFAULT 0)")
cursor.execute("CREATE TABLE IF NOT EXISTS inventory (user_id INTEGER, item TEXT)")
conn.commit()

# ===== ذاكرة الألعاب النشطة =====
solo_games = {}
quiz_games = {}
active_guess_games = {}
active_xo_games = {}

# ===== القائمة الرئيسية =====
def menu():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🎮 لعب فردي (تخمين)", callback_data="solo")],
        [InlineKeyboardButton("👥 تحدي التخمين", callback_data="challenge")],
        [InlineKeyboardButton("❌⭕ تحدي XO", callback_data="xo")],
        [InlineKeyboardButton("🧠 كويز سريع", callback_data="quiz")],
        [InlineKeyboardButton("💰 المتجر", callback_data="shop")],
        [InlineKeyboardButton("🏆 نقاطي", callback_data="points")],
        [InlineKeyboardButton("🥇 المتصدرين", callback_data="leader")]
    ])

# ===== الأمر Start =====
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    cursor.execute("INSERT OR IGNORE INTO users(user_id) VALUES (?)", (uid,))
    conn.commit()
    await update.message.reply_text("🔥 أهلاً بك في SuperGameBot PRO\nاختر من القائمة أدناه للبدء:", reply_markup=menu())

# ===== معالجة أزرار القائمة والمتجر =====
async def buttons_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    uid = q.from_user.id
    await q.answer()

    if q.data == "solo":
        solo_games[uid] = {"number": random.randint(1, 100), "tries": 5}
        await q.message.reply_text("🎮 خمن رقم بين 1 و 100 (لديك 5 محاولات)")

    elif q.data == "quiz":
        question = random.choice([("عاصمة فرنسا؟", "paris"), ("5+7=?", "12"), ("لون السماء؟", "blue")])
        quiz_games[uid] = question
        await q.message.reply_text(f"🧠 {question[0]}")

    elif q.data == "challenge":
        await q.message.reply_text("📩 لتحدي شخص في التخمين، أرسل:\n`/challenge ID`", parse_mode="Markdown")

    elif q.data == "xo":
        await q.message.reply_text("📩 لتحدي شخص في XO، أرسل:\n`/xo ID`", parse_mode="Markdown")

    elif q.data == "shop":
        kb = [[InlineKeyboardButton("🎟️ محاولة (+1) (20 pts)", callback_data="buy_try")],
              [InlineKeyboardButton("💡 تلميح (15 pts)", callback_data="buy_hint")]]
        await q.message.reply_text("🛒 مرحباً بك في المتجر:", reply_markup=InlineKeyboardMarkup(kb))

    elif q.data == "points":
        cursor.execute("SELECT points FROM users WHERE user_id=?", (uid,))
        pts = cursor.fetchone()[0]
        await q.message.reply_text(f"🏆 رصيدك الحالي: {pts} نقطة")

    elif q.data == "leader":
        await q.message.reply_text(format_leaderboard(cursor))

    elif q.data.startswith("buy_"):
        item = q.data.split("_")[1]
        cost = 20 if item == "try" else 15
        if buy_item(cursor, conn, uid, item, cost):
            await q.message.reply_text(f"✅ تم الشراء بنجاح!")
        else:
            await q.message.reply_text("❌ نقاطك غير كافية!")

# ===== أوامر التحدي (Commands) =====
async def challenge_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    if not context.args:
        await update.message.reply_text("⚠️ أرسل الـ ID الخاص بخصمك بعد الأمر.")
        return
    try:
        opponent = int(context.args[0])
        kb = [[InlineKeyboardButton("✅ قبول", callback_data=f"guess_acc_{uid}"),
               InlineKeyboardButton("❌ رفض", callback_data=f"guess_rej_{uid}")]]
        await context.bot.send_message(opponent, f"👥 تحدي تخمين جديد من {uid}!", reply_markup=InlineKeyboardMarkup(kb))
        await update.message.reply_text("📨 تم إرسال طلب التحدي.")
    except:
        await update.message.reply_text("❌ لم أتمكن من العثور على اللاعب.")

async def xo_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    if not context.args:
        await update.message.reply_text("⚠️ أرسل الـ ID الخاص بخصمك بعد الأمر.")
        return
    try:
        opponent = int(context.args[0])
        kb = [[InlineKeyboardButton("✅ قبول", callback_data=f"xo_acc_{uid}"),
               InlineKeyboardButton("❌ رفض", callback_data=f"xo_rej_{uid}")]]
        await context.bot.send_message(opponent, f"❌⭕ تحدي XO جديد من {uid}!", reply_markup=InlineKeyboardMarkup(kb))
        await update.message.reply_text("📨 تم إرسال طلب التحدي.")
    except:
        await update.message.reply_text("❌ اللاعب لم يبدأ البوت بعد.")

# ===== معالجة القبول والرفض (Callback) =====
async def handle_invites(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    uid = q.from_user.id
    data = q.data
    challenger = int(data.split("_")[2])
    await q.answer()

    if "acc" in data:
        if data.startswith("guess"):
            num = random.randint(1, 100)
            active_guess_games[uid] = active_guess_games[challenger] = {"op": challenger if uid != challenger else uid, "number": num, "turn": challenger, "tries": 5}
            await context.bot.send_message(challenger, "🔥 خصمك قبل التحدي! دورك للتخمين.")
            await q.edit_message_text("✅ بدأت اللعبة!")
        
        elif data.startswith("xo"):
            board = [" "] * 9
            game_data = {"p1": challenger, "p2": uid, "board": board, "turn": challenger}
            active_xo_games[uid] = active_xo_games[challenger] = game_data
            await context.bot.send_message(challenger, "🎮 بدأت لعبة XO! دورك (X):", reply_markup=draw_xo_keyboard(board))
            await q.edit_message_text("✅ قبلت التحدي! انتظر دور الخصم (O).", reply_markup=draw_xo_keyboard(board))
    else:
        await context.bot.send_message(challenger, "❌ تم رفض طلبك.")
        await q.edit_message_text("❌ قمت برفض التحدي.")

# ===== معالجة لعب XO بالأزرار =====
async def handle_xo_play(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    uid = q.from_user.id
    pos = int(q.data.split("_")[2])
    
    if uid not in active_xo_games:
        await q.answer("❌ انتهت هذه اللعبة.", show_alert=True)
        return

    game = active_xo_games[uid]
    if game["turn"] != uid:
        await q.answer("⏳ انتظر دورك!", show_alert=True)
        return

    board = game["board"]
    if board[pos] != " ":
        await q.answer("❌ المكان مشغول!", show_alert=True)
        return

    # تنفيذ الحركة
    board[pos] = "X" if uid == game["p1"] else "O"
    winner = check_xo_win(board)
    await q.answer()

    if winner:
        res = f"🎉 الفائز: {winner}" if winner != "Draw" else "🤝 تعادل!"
        if winner != "Draw":
            cursor.execute("UPDATE users SET points = points + 20 WHERE user_id = ?", (uid,))
            conn.commit()
        
        await q.edit_message_text(f"{res}\nانتهت اللعبة.", reply_markup=draw_xo_keyboard(board))
        op = game["p2"] if uid == game["p1"] else game["p1"]
        await context.bot.send_message(op, f"{res}\nانتهت اللعبة.", reply_markup=draw_xo_keyboard(board))
        del active_xo_games[game["p1"]], active_xo_games[game["p2"]]
    else:
        game["turn"] = game["p2"] if uid == game["p1"] else game["p1"]
        await q.edit_message_text("⌛ انتظر الخصم...", reply_markup=draw_xo_keyboard(board))
        await context.bot.send_message(game["turn"], "🔥 دورك الآن:", reply_markup=draw_xo_keyboard(board))

# ===== معالجة الرسائل النصية (التخمين والكويز) =====
async def message_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    txt = update.message.text.lower()

    if uid in solo_games:
        # منطق التخمين الفردي (كما هو في كودك)
        pass 

    elif uid in active_guess_games:
        # منطق التخمين الجماعي (كما هو في كودك)
        pass

# ===== التشغيل =====
def main():
    async def post_init(application):
        """هذه الدالة تعمل فور تشغيل البوت لتسجيل قائمة الأوامر"""
        commands = [
            BotCommand("start", "الرجوع للقائمة الرئيسية 🔥"),
            BotCommand("challenge", "تحدي صديق في لعبة التخمين 👥"),
            BotCommand("xo", "تحدي صديق في لعبة XO ❌⭕"),
        ]
        await application.bot.set_my_commands(commands)
    
    #app = ApplicationBuilder().token(TOKEN).build()
    app = ApplicationBuilder().token(TOKEN).post_init(post_init).build()
    
    # 1. الأوامر
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("challenge", challenge_cmd))
    app.add_handler(CommandHandler("xo", xo_cmd))

    # 2. الأزرار (يجب ترتيبها من الأكثر تخصيصاً إلى الأعم)
    app.add_handler(CallbackQueryHandler(handle_xo_play, pattern="^xo_play_"))
    app.add_handler(CallbackQueryHandler(handle_invites, pattern="^(guess|xo)_(acc|rej)_"))
    app.add_handler(CallbackQueryHandler(buttons_handler))

    # 3. النصوص
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, message_handler))

    print("🚀 SuperGameBot PRO is Online!")
    app.run_polling()

if __name__ == "__main__":
    main()
