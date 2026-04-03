# utils.py
import sqlite3
import random
from telegram import InlineKeyboardButton, InlineKeyboardMarkup

# ===== XO =====

# الدالة الجديدة لإنشاء لوحة الأزرار التفاعلية
def draw_xo_keyboard(board):
    keyboard = []
    # نقسم المصفوفة (9 خانات) إلى 3 صفوف
    for i in range(0, 9, 3):
        row = []
        for j in range(i, i + 3):
            # نضع إيموجي للمربعات الفارغة ليكون شكلها أفضل
            label = board[j] if board[j] != " " else "⬜"
            # كل زر يرسل رقم الخانة (من 0 إلى 8) عند الضغط عليه
            row.append(InlineKeyboardButton(label, callback_data=f"xo_play_{j}"))
        keyboard.append(row)
    return InlineKeyboardMarkup(keyboard)

# دالة التحقق من الفوز (بقيت كما هي لأن المنطق لم يتغير)
def check_xo_win(board):
    win_cond = [
        [0, 1, 2], [3, 4, 5], [6, 7, 8], # أفقي
        [0, 3, 6], [1, 4, 7], [2, 5, 8], # عمودي
        [0, 4, 8], [2, 4, 6]             # قطري
    ]
    for cond in win_cond:
        a, b, c = cond
        if board[a] == board[b] == board[c] and board[a] != " ":
            return board[a]
    if " " not in board:
        return "Draw"
    return None

# ===== Leaderboard =====
def format_leaderboard(cursor, limit=10):
    cursor.execute("SELECT user_id, points FROM users ORDER BY points DESC LIMIT ?", (limit,))
    top = cursor.fetchall()
    txt = "🥇 **قائمة المتصدرين:**\n"
    txt += "---" * 5 + "\n"
    for i, u in enumerate(top, 1):
        txt += f"{i}. `ID: {u[0]}` — **{u[1]}** pts\n"
    return txt

# ===== متجر (Shop) =====
def buy_item(cursor, conn, user_id, item, cost):
    cursor.execute("SELECT points FROM users WHERE user_id=?", (user_id,))
    result = cursor.fetchone()
    if not result:
        return False
        
    pts = result[0]
    if pts < cost:
        return False
    
    # خصم النقاط وإضافة العنصر للمخزن
    cursor.execute("UPDATE users SET points = points - ? WHERE user_id=?", (cost, user_id))
    cursor.execute("INSERT INTO inventory(user_id, item) VALUES(?, ?)", (user_id, item))
    conn.commit()
    return True