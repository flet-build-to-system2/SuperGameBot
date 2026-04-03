# utils.py
import sqlite3
import random

# ===== XO =====
def draw_board(board):
    return f"""
 {board[0]} | {board[1]} | {board[2]}
---+---+---
 {board[3]} | {board[4]} | {board[5]}
---+---+---
 {board[6]} | {board[7]} | {board[8]}
"""

def check_xo_win(board):
    win_cond = [
        [0,1,2],[3,4,5],[6,7,8],
        [0,3,6],[1,4,7],[2,5,8],
        [0,4,8],[2,4,6]
    ]
    for cond in win_cond:
        a,b,c = cond
        if board[a]==board[b]==board[c] and board[a]!=" ":
            return board[a]
    if " " not in board:
        return "Draw"
    return None

# ===== Leaderboard =====
def format_leaderboard(cursor, limit=10):
    cursor.execute("SELECT user_id, points FROM users ORDER BY points DESC LIMIT ?", (limit,))
    top = cursor.fetchall()
    txt = "🥇 الترتيب:\n"
    for i,u in enumerate(top,1):
        txt += f"{i}. {u[0]} - {u[1]} pts\n"
    return txt

# ===== متجر =====
def buy_item(cursor, conn, user_id, item, cost):
    cursor.execute("SELECT points FROM users WHERE user_id=?", (user_id,))
    pts = cursor.fetchone()[0]
    if pts < cost:
        return False
    cursor.execute("UPDATE users SET points = points - ? WHERE user_id=?", (cost, user_id))
    cursor.execute("INSERT INTO inventory(user_id,item) VALUES(?,?)", (user_id, item))
    conn.commit()
    return True