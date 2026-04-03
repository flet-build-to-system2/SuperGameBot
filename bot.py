import random
import sqlite3
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, BotCommand
from telegram.ext import ApplicationBuilder, CommandHandler, CallbackQueryHandler, MessageHandler, filters, ContextTypes
from utils import draw_xo_keyboard, check_xo_win, buy_item, format_leaderboard

# ⚠️ تأكد من حماية التوكن الخاص بك
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

# ===== تسجيل الأوامر في قائمة التلغرام =====
async def post_init(application):
    commands = [
        BotCommand("start", "القائمة الرئيسية 🏠"),
        BotCommand("challenge", "تحدي تخمين (ID الخصم) 👥"),
        BotCommand("xo", "تحدي اكس او (ID الخصم) ❌⭕"),
    ]
    await application.bot.set_my_commands(commands)

# ===== القائمة الرئيسية =====
def main_menu():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🎮 لعب فردي", callback_data="solo")],
        [InlineKeyboardButton("👥 تحدي تخمين", callback_data="challenge_info")],
        [InlineKeyboardButton("❌⭕ تحدي XO", callback_data="xo_info")],
        [InlineKeyboardButton("🧠 كويز سريع", callback_data="quiz")],
        [InlineKeyboardButton("💰 المتجر", callback_data="shop")],
        [InlineKeyboardButton("🏆 رصيدي", callback_data="points")],
        [InlineKeyboardButton("🥇 المتصدرين", callback_data="leader")]
    ])

# ===== الأوامر الأساسية =====
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    cursor.execute("INSERT OR IGNORE INTO users(user_id) VALUES (?)", (uid,))
    conn.commit()
    await update.message.reply_text("🔥 مرحباً بك في SuperGameBot PRO!\nاختر لعبة للبدء:", reply_markup=main_menu())

async def challenge_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    if not context.args:
        await update.message.reply_text("⚠️ استعمل: `/challenge ID_الخصم`", parse_mode="Markdown")
        return
    try:
        opponent = int(context.args[0])
        if opponent == uid:
            await update.message.reply_text("❌ لا يمكنك تحدي نفسك!")
            return
        kb = [[InlineKeyboardButton("✅ قبول", callback_data=f"guess_acc_{uid}"),
               InlineKeyboardButton("❌ رفض", callback_data=f"guess_rej_{uid}")]]
        await context.bot.send_message(opponent, f"👥 تحدي تخمين جديد من {uid}!", reply_markup=InlineKeyboardMarkup(kb))
        await update.message.reply_text("📨 تم إرسال طلب التحدي بنجاح.")
    except:
        await update.message.reply_text("❌ تعذر إرسال الطلب. تأكد من الـ ID.")

async def xo_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    if not context.args:
        await update.message.reply_text("⚠️ استعمل: `/xo ID_الخصم`", parse_mode="Markdown")
        return
    try:
        opponent = int(context.args[0])
        if opponent == uid:
            await update.message.reply_text("❌ لا يمكنك تحدي نفسك!")
            return
        kb = [[InlineKeyboardButton("✅ قبول", callback_data=f"xo_acc_{uid}"),
               InlineKeyboardButton("❌ رفض", callback_data=f"xo_rej_{uid}")]]
        await context.bot.send_message(opponent, f"❌⭕ تحدي XO جديد من {uid}!", reply_markup=InlineKeyboardMarkup(kb))
        await update.message.reply_text("📨 تم إرسال طلب التحدي بنجاح.")
    except:
        await update.message.reply_text("❌ تعذر إرسال الطلب.")

# ===== معالجة أزرار القائمة =====
async def menu_buttons(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    uid = q.from_user.id
    await q.answer()

    if q.data == "solo":
        solo_games[uid] = {"num": random.randint(1, 100), "tries": 5}
        await q.message.reply_text("🎮 خمن رقم بين 1 و 100 (لديك 5 محاولات):")
    elif q.data == "quiz":
        question = random.choice([("عاصمة فرنسا؟", "باريس"), ("5+7=?", "12"), ("لون السماء؟", "ازرق")])
        quiz_games[uid] = question
        await q.message.reply_text(f"🧠 {question[0]}")
    elif q.data == "challenge_info":
        await q.message.reply_text("📩 لتحدي شخص، أرسل بالدردشة: `/challenge ID`", parse_mode="Markdown")
    elif q.data == "xo_info":
        await q.message.reply_text("📩 لتحدي شخص، أرسل بالدردشة: `/xo ID`", parse_mode="Markdown")
    elif q.data == "points":
        cursor.execute("SELECT points FROM users WHERE user_id=?", (uid,))
        await q.message.reply_text(f"🏆 رصيدك: {cursor.fetchone()[0]} نقطة.")
    elif q.data == "leader":
        await q.message.reply_text(format_leaderboard(cursor))
    elif q.data == "shop":
        kb = [[InlineKeyboardButton("🎟️ محاولة إضافية (20)", callback_data="buy_try")]]
        await q.message.reply_text("🛒 المتجر:", reply_markup=InlineKeyboardMarkup(kb))
    elif q.data == "buy_try":
        if buy_item(cursor, conn, uid, "try", 20):
            await q.message.reply_text("✅ تم الشراء بنجاح!")
        else:
            await q.message.reply_text("❌ نقاطك غير كافية.")

# ===== معالجة قبول التحديات ومزامنة الألعاب =====
async def handle_invites(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    uid = q.from_user.id
    data = q.data
    challenger = int(data.split("_")[2])
    await q.answer()

    if "acc" in data:
        if data.startswith("guess"):
            num = random.randint(1, 100)
            # تم الإصلاح هنا: كل لاعب يسجل الخصم الصحيح له
            active_guess_games[uid] = {"op": challenger, "number": num, "turn": challenger, "tries": 5}
            active_guess_games[challenger] = {"op": uid, "number": num, "turn": challenger, "tries": 5}
            
            await context.bot.send_message(challenger, "🔥 خصمك قبل التحدي! ابدأ بالتخمين الآن.")
            await q.edit_message_text("✅ بدأت اللعبة! انتظر دور الخصم.")
            
        elif data.startswith("xo"):
            board = [" "] * 9
            game_obj = {"p1": challenger, "p2": uid, "board": board, "turn": challenger}
            active_xo_games[uid] = active_xo_games[challenger] = game_obj
            await context.bot.send_message(challenger, "🎮 بدأت اللعبة! دورك (X):", reply_markup=draw_xo_keyboard(board))
            await q.edit_message_text("✅ قبلت التحدي! انتظر دور الخصم (O).", reply_markup=draw_xo_keyboard(board))
    else:
        await context.bot.send_message(challenger, "❌ تم رفض طلبك.")
        await q.edit_message_text("❌ تم الرفض.")

# ===== معالجة لعب XO بالأزرار =====
async def handle_xo_play(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    uid = q.from_user.id
    pos = int(q.data.split("_")[2])
    if uid not in active_xo_games: return
    
    game = active_xo_games[uid]
    if game["turn"] != uid:
        await q.answer("⏳ ليس دورك الآن!", show_alert=True); return
    
    board = game["board"]
    if board[pos] != " ": return

    symbol = "X" if uid == game["p1"] else "O"
    board[pos] = symbol
    winner = check_xo_win(board)
    await q.answer()

    if winner:
        res_txt = f"🎉 الفائز هو: {symbol}" if winner != "Draw" else "🤝 تعادل!"
        if winner != "Draw":
            cursor.execute("UPDATE users SET points = points + 20 WHERE user_id = ?", (uid,))
            conn.commit()
        
        await q.edit_message_text(f"{res_txt}\nانتهت المباراة.", reply_markup=draw_xo_keyboard(board))
        op = game["p2"] if uid == game["p1"] else game["p1"]
        await context.bot.send_message(op, f"{res_txt}\nانتهت المباراة.", reply_markup=draw_xo_keyboard(board))
        del active_xo_games[game["p1"]], active_xo_games[game["p2"]]
    else:
        next_op = game["p2"] if uid == game["p1"] else game["p1"]
        game["turn"] = next_op
        await q.edit_message_text("⌛ تم، انتظر الخصم...", reply_markup=draw_xo_keyboard(board))
        await context.bot.send_message(next_op, "🔥 دورك الآن:", reply_markup=draw_xo_keyboard(board))

# ===== معالجة الرسائل النصية (التخمين والكويز) =====
async def text_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    txt = update.message.text.strip().lower()

    # 1. كويز سريع
    if uid in quiz_games:
        q_text, ans = quiz_games[uid]
        if txt == ans.lower():
            cursor.execute("UPDATE users SET points = points + 5 WHERE user_id = ?", (uid,))
            conn.commit()
            await update.message.reply_text("✅ صح! حصلت على +5 نقاط.")
        else:
            await update.message.reply_text(f"❌ خطأ، الإجابة هي: {ans}")
        del quiz_games[uid]; return

    # 2. تخمين فردي
    if uid in solo_games:
        game = solo_games[uid]
        try: g = int(txt)
        except: return
        game["tries"] -= 1
        if g == game["num"]:
            cursor.execute("UPDATE users SET points = points + 10 WHERE user_id = ?", (uid,))
            conn.commit()
            await update.message.reply_text(f"🎉 صحيح! الرقم هو {g}. مبروك +10.")
            del solo_games[uid]
        elif game["tries"] <= 0:
            await update.message.reply_text(f"💀 خسرت! الرقم كان {game['num']}.")
            del solo_games[uid]
        else:
            hint = "أصغر 📉" if g > game["num"] else "أكبر 📈"
            await update.message.reply_text(f"{hint} | محاولات متبقية: {game['tries']}")
        return

    # 3. تحدي التخمين (الإصلاح الجذري هنا)
    if uid in active_guess_games:
        game = active_guess_games[uid]
        op = game["op"]
        
        if game["turn"] != uid:
            await update.message.reply_text("⏳ انتظر دور خصمك للتخمين!"); return

        try: g = int(txt)
        except: return
        
        game["tries"] -= 1
        # تحديث المزامنة للطرفين
        active_guess_games[op]["tries"] = game["tries"]

        if g == game["number"]:
            cursor.execute("UPDATE users SET points = points + 30 WHERE user_id = ?", (uid,))
            conn.commit()
            await update.message.reply_text("🏆 فزت في التحدي! +30 نقطة.")
            await context.bot.send_message(op, f"❌ خسررت! الخصم خمن الرقم الصحيح ({g}).")
            del active_guess_games[uid], active_guess_games[op]
        elif game["tries"] <= 0:
            await update.message.reply_text(f"❌ انتهت المحاولات! الرقم كان {game['number']}.")
            await context.bot.send_message(op, f"🏆 فزت! الخصم استنفد جميع محاولاته. الرقم كان {game['number']}.")
            del active_guess_games[uid], active_guess_games[op]
        else:
            hint = "أصغر 📉" if g > game["number"] else "أكبر 📈"
            # تبديل الدور بشكل صحيح
            game["turn"] = op
            active_guess_games[op]["turn"] = op
            
            await update.message.reply_text(f"خطأ! الرقم {hint}. دور الخصم الآن.")
            # إرسال الرسالة للخصم (op) وليس لنفس الشخص (uid)
            await context.bot.send_message(op, f"🎯 دورك الآن!\nالخصم خمن {g} والنتيجة خمن الآن:")

# ===== تشغيل التطبيق =====
def main():
    app = ApplicationBuilder().token(TOKEN).post_init(post_init).build()
    
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("challenge", challenge_cmd))
    app.add_handler(CommandHandler("xo", xo_cmd))
    
    app.add_handler(CallbackQueryHandler(handle_xo_play, pattern="^xo_play_"))
    app.add_handler(CallbackQueryHandler(handle_invites, pattern="^(guess|xo)_(acc|rej)_"))
    app.add_handler(CallbackQueryHandler(menu_buttons))
    
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, text_handler))

    print("🚀 SuperGameBot PRO is Running...")
    app.run_polling()

if __name__ == "__main__":
    main()
