from flask import Flask, render_template
import sqlite3

app = Flask(__name__)
DB = "../db.sqlite"  # تأكد أن المسار صحيح للخدمة

@app.route("/")
def index():
    conn = sqlite3.connect(DB)
    cursor = conn.cursor()
    cursor.execute("SELECT user_id, points FROM users ORDER BY points DESC LIMIT 10")
    top = cursor.fetchall()
    conn.close()
    return render_template("index.html", top=top)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080)