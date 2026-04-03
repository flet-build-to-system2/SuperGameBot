import sqlite3
import random, os

DB = "db.sqlite"
conn = sqlite3.connect(DB, check_same_thread=False)
cursor = conn.cursor()

def get_solo_number():
    return random.randint(1,100)

def update_points(uid, pts):
    cursor.execute("UPDATE users SET points = points + ? WHERE user_id=?", (pts, uid))
    conn.commit()

def start_xo_game(player1, player2):
    board = "---------"
    cursor.execute("""
        INSERT INTO xo_games(player1, player2, board, turn, winner)
        VALUES (?, ?, ?, ?, NULL)
    """,(player1, player2, board, player1))
    conn.commit()