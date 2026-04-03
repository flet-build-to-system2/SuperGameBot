import sqlite3
from telegram import InlineKeyboardButton, InlineKeyboardMarkup

# --- لوحة أزرار XO ---
def draw_xo_keyboard(board):
    keyboard = []
    for i in range(0, 9, 3):
        row = []
        for j in range(i, i + 3):
            label = board[j] if board[j] != " " else "⬜"
            row.append(InlineKeyboardButton(label, callback_data=f"xo_play_{j}"))
        keyboard.append(row)
    return InlineKeyboardMarkup(keyboard)

# --- التحقق من فوز XO ---
def check_xo_win(board):
    win_cond = [
        [0, 1, 2], [3, 4, 5], [6, 7, 8],
        [0, 3, 6], [1, 4, 7], [2, 5, 8],
        [0, 4, 8], [2, 4, 6]
    ]
    for cond in win_cond:
        a, b, c = cond
        if board[a] == board[b] == board[c] and board[a] != " ":
            return board[a]
    if " " not in board:
        return "Draw"
    return None

# --- لوحة الصدارة ---
def format_leaderboard(cursor, limit=10):
    cursor.execute("SELECT user_id, points FROM users ORDER BY points DESC LIMIT ?", (limit,))
    top = cursor.fetchall()
    txt = "🏆 **قائمة المتصدرين:**\n\n"
    for i, u in enumerate(top, 1):
        txt += f"{i}. `ID: {u[0]}` — **{u[1]}** نقطة\n"
    return txt

# --- الشراء من المتجر ---
def buy_item(cursor, conn, user_id, item, cost):
    cursor.execute("SELECT points FROM users WHERE user_id=?", (user_id,))
    res = cursor.fetchone()
    if not res or res[0] < cost:
        return False
    cursor.execute("UPDATE users SET points = points - ? WHERE user_id=?", (cost, user_id))
    cursor.execute("INSERT INTO inventory(user_id, item) VALUES(?, ?)", (user_id, item))
    conn.commit()
    return True
