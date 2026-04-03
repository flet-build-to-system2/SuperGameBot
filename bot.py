import random
import sqlite3
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, BotCommand
from telegram.ext import ApplicationBuilder, CommandHandler, CallbackQueryHandler, MessageHandler, filters, ContextTypes
from utils import draw_xo_keyboard, check_xo_win, buy_item, format_leaderboard

TOKEN = "8777038264:AAGr6TwS2mXccJqE-bI2QTGJ-QAGmw_pNbA"

conn = sqlite3.connect("db.sqlite", check_same_thread=False)
cursor = conn.cursor()
cursor.execute("CREATE TABLE IF NOT EXISTS users (user_id INTEGER PRIMARY KEY, points INTEGER DEFAULT 0)")
cursor.execute("CREATE TABLE IF NOT EXISTS inventory (user_id INTEGER, item TEXT)")
conn.commit()

solo_games = {}
quiz_games = {}
active_guess_games = {}
active_xo_games = {}

async def post_init(application):
    commands = [
        BotCommand("start", "القائمة الرئيسية 🏠"),
        BotCommand("challenge", "تحدي تخمين (ID الخصم) 👥"),
        BotCommand("xo", "تحدي اكس او (ID الخصم) ❌⭕"),
    ]
    await application.bot.set_my_commands(commands)

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

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    cursor.execute("INSERT OR IGNORE INTO users(user_id) VALUES (?)", (uid,))
    conn.commit()
    await update.message.reply_text("🔥 مرحباً بك في SuperGameBot PRO!", reply_markup=main_menu())

async def challenge_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    if not context.args:
        await update.message.reply_text("⚠️ استعمل: `/challenge ID`", parse_mode="Markdown")
        return
    try:
        opponent = int(context.args[0])
        kb = [[InlineKeyboardButton("✅ قبول", callback_data=f"guess_acc_{uid}"),
               InlineKeyboardButton("❌ رفض", callback_data=f"guess_rej_{uid}")]]
        await context.bot.send_message(opponent, f"👥 تحدي تخمين جديد من {uid}!", reply_markup=InlineKeyboardMarkup(kb))
        await update.message.reply_text("📨 تم إرسال الطلب بنجاح.")
    except:
        await update.message.reply_text("❌ تعذر العثور على اللاعب.")

async def xo_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    if not context.args:
        await update.message.reply_text("⚠️ استعمل: `/xo ID`", parse_mode="Markdown")
        return
    try:
        opponent = int(context.args[0])
        kb = [[InlineKeyboardButton("✅ قبول", callback_data=f"xo_acc_{uid}"),
               InlineKeyboardButton("❌ رفض", callback_data=f"xo_rej_{uid}")]]
        await context.bot.send_message(opponent, f"❌⭕ تحدي XO جديد من {uid}!", reply_markup=InlineKeyboardMarkup(kb))
        await update.message.reply_text("📨 تم إرسال الطلب.")
    except:
        await update.message.reply_text("❌ اللاعب غير متاح.")

async def menu_buttons(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    uid = q.from_user.id
    await q.answer()
    if q.data == "solo":
        solo_games[uid] = {"num": random.randint(1, 100), "tries": 5}
        await q.message.reply_text("🎮 خمن رقم بين 1 و 100 (5 محاولات):")
    elif q.data == "quiz":
        question = random.choice([("عاصمة فرنسا؟", "باريس"), ("5+7=?", "12"), ("لون السماء؟", "ازرق")])
        quiz_games[uid] = question
        await q.message.reply_text(f"🧠 {question[0]}")
    elif q.data == "points":
        cursor.execute("SELECT points FROM users WHERE user_id=?", (uid,))
        await q.message.reply_text(f"🏆 نقاطك: {cursor.fetchone()[0]}")
    elif q.data == "leader":
        await q.message.reply_text(format_leaderboard(cursor))
    elif q.data == "shop":
        kb = [[InlineKeyboardButton("🎟️ محاولة (20)", callback_data="buy_try")]]
        await q.message.reply_text("🛒 المتجر:", reply_markup=InlineKeyboardMarkup(kb))

async def handle_invites(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    uid = q.from_user.id
    challenger = int(q.data.split("_")[2])
    await q.answer()
    if "acc" in q.data:
        if q.data.startswith("guess"):
            num = random.randint(1, 100)
            game = {"op": challenger, "number": num, "turn": challenger, "tries": 5}
            active_guess_games[uid] = active_guess_games[challenger] = game
            await context.bot.send_message(challenger, "🔥 خصمك قبل! ابدأ بالتخمين.")
            await q.edit_message_text("✅ بدأت اللعبة!")
        elif q.data.startswith("xo"):
            board = [" "] * 9
            game = {"p1": challenger, "p2": uid, "board": board, "turn": challenger}
            active_xo_games[uid] = active_xo_games[challenger] = game
            await context.bot.send_message(challenger, "🎮 دورك (X):", reply_markup=draw_xo_keyboard(board))
            await q.edit_message_text("✅ قبلت التحدي!", reply_markup=draw_xo_keyboard(board))
    else:
        await context.bot.send_message(challenger, "❌ رفض الخصم طلبك.")
        await q.edit_message_text("❌ تم الرفض.")

async def handle_xo_play(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    uid = q.from_user.id
    pos = int(q.data.split("_")[2])
    if uid not in active_xo_games: return
    game = active_xo_games[uid]
    if game["turn"] != uid:
        await q.answer("⏳ ليس دورك!", show_alert=True); return
    board = game["board"]
    if board[pos] != " ": return
    board[pos] = "X" if uid == game["p1"] else "O"
    winner = check_xo_win(board)
    if winner:
        msg = f"🎉 الفائز: {winner}" if winner != "Draw" else "🤝 تعادل!"
        await q.edit_message_text(msg, reply_markup=draw_xo_keyboard(board))
        op = game["p2"] if uid == game["p1"] else game["p1"]
        await context.bot.send_message(op, msg, reply_markup=draw_xo_keyboard(board))
        del active_xo_games[game["p1"]], active_xo_games[game["p2"]]
    else:
        game["turn"] = game["p2"] if uid == game["p1"] else game["p1"]
        await q.edit_message_text("⌛ انتظر الخصم...", reply_markup=draw_xo_keyboard(board))
        await context.bot.send_message(game["turn"], "🔥 دورك الآن:", reply_markup=draw_xo_keyboard(board))

async def text_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    txt = update.message.text.strip().lower()
    if uid in quiz_games:
        q, ans = quiz_games[uid]
        if txt == ans.lower():
            cursor.execute("UPDATE users SET points=points+5 WHERE user_id=?", (uid,))
            conn.commit()
            await update.message.reply_text("✅ صح! +5")
        else: await update.message.reply_text(f"❌ خطأ، الحل: {ans}")
        del quiz_games[uid]; return
    if uid in solo_games:
        g = int(txt); game = solo_games[uid]; game["tries"]-=1
        if g == game["num"]:
            cursor.execute("UPDATE users SET points=points+10 WHERE user_id=?", (uid,))
            conn.commit(); await update.message.reply_text("🎉 صح!"); del solo_games[uid]
        elif game["tries"]<=0: await update.message.reply_text(f"💀 خسرت! {game['num']}"); del solo_games[uid]
        else: await update.message.reply_text("أكبر 📈" if g < game["num"] else "أصغر 📉")
        return
    if uid in active_guess_games:
        game = active_guess_games[uid]
        op = game["op"]
        if game["turn"] != uid: return
        try: g = int(txt)
        except: return
        game["tries"] -= 1
        active_guess_games[op]["tries"] = game["tries"]
        if g == game["number"]:
            cursor.execute("UPDATE users SET points=points+30 WHERE user_id=?", (uid,))
            conn.commit()
            await update.message.reply_text("🏆 فزت! +30")
            await context.bot.send_message(op, f"❌ خسررت! الرقم {g}")
            del active_guess_games[uid], active_guess_games[op]
        elif game["tries"] <= 0:
            await update.message.reply_text(f"❌ انتهت المحاولات! {game['number']}")
            await context.bot.send_message(op, "🏆 فزت! الخصم خسر.")
            del active_guess_games[uid], active_guess_games[op]
        else:
            hint = "أصغر 📉" if g > game["number"] else "أكبر 📈"
            game["turn"] = op
            active_guess_games[op]["turn"] = op
            await update.message.reply_text(f"خطأ! الرقم {hint}. دور خصمك الآن.")
            await context.bot.send_message(op, f"🎯 دورك الآن!\nالخصم خمن {g} والنتيجة {hint}.\nخمن:")

def main():
    app = ApplicationBuilder().token(TOKEN).post_init(post_init).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("challenge", challenge_cmd))
    app.add_handler(CommandHandler("xo", xo_cmd))
    app.add_handler(CallbackQueryHandler(handle_xo_play, pattern="^xo_play_"))
    app.add_handler(CallbackQueryHandler(handle_invites, pattern="^(guess|xo)_(acc|rej)_"))
    app.add_handler(CallbackQueryHandler(menu_buttons))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, text_handler))
    app.run_polling()

if __name__ == "__main__":
    main()
