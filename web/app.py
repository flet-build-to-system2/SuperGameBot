from flask import Flask, render_template
import sqlite3
import os

app = Flask(__name__)
# استخدم المسار النسبي بالنسبة لسيرفر Railway
DB = os.path.join(os.path.dirname(__file__), "../db.sqlite")

def get_db():
    conn = sqlite3.connect(DB)
    conn.row_factory = sqlite3.Row
    return conn

@app.route("/")
def index():
    conn = get_db()
    cursor = conn.cursor()

    # Leaderboard
    cursor.execute("SELECT user_id, points FROM users ORDER BY points DESC LIMIT 10")
    leaderboard = cursor.fetchall()

    # Users & Points
    cursor.execute("SELECT * FROM users")
    users = cursor.fetchall()

    # Inventory
    cursor.execute("SELECT * FROM inventory")
    inventory = cursor.fetchall()

    # Placeholder للألعاب الجارية
    active_games = {
        "solo": [],
        "challenge": [],
        "xo": []
    }

    return render_template(
        "index.html",
        leaderboard=leaderboard,
        users=users,
        inventory=inventory,
        active_games=active_games
    )

# تشغيل على PORT الخاص بـ Railway
if __name__=="__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)