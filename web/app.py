import os
import sqlite3
from flask import Flask, render_template

app = Flask(__name__)

DB = os.path.join(os.path.dirname(__file__), "../db.sqlite")
conn = sqlite3.connect(DB, check_same_thread=False)
cursor = conn.cursor()

@app.route('/')
def index():
    try:
        cursor.execute("SELECT user_id, points FROM users ORDER BY points DESC LIMIT 10")
        top = cursor.fetchall()
    except sqlite3.OperationalError:
        top = []
    return render_template("index.html", top=top)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 8080)))