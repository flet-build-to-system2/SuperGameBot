# web/app.py
from flask import Flask, render_template
import sqlite3
app = Flask(__name__)

conn = sqlite3.connect("../db.sqlite", check_same_thread=False)
cursor = conn.cursor()

@app.route("/")
def home():
    cursor.execute("SELECT COUNT(*), SUM(points) FROM users")
    users,total_points = cursor.fetchone()
    return render_template("index.html", users=users, points=total_points)

if __name__=="__main__":
    app.run(host="0.0.0.0", port=5000)