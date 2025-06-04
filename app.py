from flask import Flask, render_template, request, redirect, url_for, session, jsonify, render_template_string
from werkzeug.security import generate_password_hash, check_password_hash
import os
import sqlite3

app = Flask(__name__)
app.secret_key = 'your_secret_key'
DB_FILE = 'users.db'
COMMANDS_FILE = 'commands.txt'
ANNOUNCEMENT_FILE = 'announcement.txt'

# Initialize the database
def init_db():
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE,
        password TEXT
    )''')
    conn.commit()
    conn.close()

init_db()

# Ensure files exist
if not os.path.exists(COMMANDS_FILE):
    with open(COMMANDS_FILE, "w", encoding="utf-8") as f:
        pass

if not os.path.exists(ANNOUNCEMENT_FILE):
    with open(ANNOUNCEMENT_FILE, "w", encoding="utf-8") as f:
        f.write("No announcements yet.")

@app.route("/")
def index():
    return redirect(url_for('login'))

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]
        user_db = {

            "raiyan": "pass123",
            "admin": "admin@123",
            "ashish": "welcome2025",
            "Rain": "Rainrain123"}
        if username in user_db and user_db[username] == password:
            session["username"] = "admin"
            return redirect(url_for("admin_panel"))

        conn = sqlite3.connect(DB_FILE)
        c = conn.cursor()
        c.execute("SELECT password FROM users WHERE username = ?", (username,))
        result = c.fetchone()
        conn.close()

        if result and check_password_hash(result[0], password):
            session["username"] = username
            return redirect(url_for("chatbot"))
        else:
            return render_template("login.html", error="Invalid credentials.")
    return render_template("login.html")

@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        username = request.form["username"]
        password = generate_password_hash(request.form["password"])

        conn = sqlite3.connect(DB_FILE)
        c = conn.cursor()
        try:
            c.execute("INSERT INTO users (username, password) VALUES (?, ?)", (username, password))
            conn.commit()
        except sqlite3.IntegrityError:
            conn.close()
            return render_template("register.html", error="Username already exists.")
        conn.close()
        return redirect(url_for("login"))
    return render_template("register.html")

@app.route("/chatbot")
def chatbot():
    if "username" not in session or session.get("username") == "admin":
        return redirect(url_for("login"))
    return render_template("chatbot.html")

@app.route("/commands")
def commands():
    if not os.path.exists(COMMANDS_FILE):
        return jsonify({"commands": []})
    with open(COMMANDS_FILE, "r") as f:
        lines = [line.strip() for line in f if '=' in line]
    return jsonify({"commands": lines})

@app.route("/logout")
def logout():
    session.pop("username", None)
    return redirect(url_for("login"))

# Admin panel access check
def admin_only():
    if session.get("username") != "admin":
        return redirect(url_for("login"))

# Admin HTML UI
ADMIN_HTML = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8" />
    <title>HCO Admin Panel</title>
    <style>
        body { font-family: Arial, sans-serif; background: #121212; color: #e0e0e0; padding: 20px; }
        h1 { color: #00ff99; }
        label { display: block; margin-top: 15px; font-weight: bold; }
        input[type=text], textarea {
            width: 100%; padding: 8px; margin-top: 5px; border-radius: 4px; border: none;
            background: #222; color: #e0e0e0; font-size: 1em;
        }
        button {
            margin-top: 15px; padding: 10px 20px; font-size: 1em;
            background: #00ff99; color: #121212; border: none; border-radius: 4px;
            cursor: pointer;
        }
        .success { margin-top: 10px; color: #00ff99; }
        .error { margin-top: 10px; color: #ff4444; }
        hr { margin-top: 40px; margin-bottom: 40px; border: 1px solid #333; }
    </style>
</head>
<body>
    <h1>HACKERS COLONY OFFICIAL Admin Panel</h1>

    <form id="commandForm">
        <label for="command">Attack Command Name:</label>
        <input type="text" id="command" name="command" placeholder="e.g. ss7 attack" required />

        <label for="link">Video Link:</label>
        <input type="text" id="link" name="link" placeholder="https://example.com/video" required />

        <button type="submit">Add / Update Command</button>
        <div id="cmdMessage"></div>
    </form>

    <hr />

    <form id="announcementForm">
        <label for="announcement">Broadcast Announcement / Notice:</label>
        <textarea id="announcement" name="announcement" rows="4" placeholder="Type announcement here..."></textarea>

        <button type="submit">Update Announcement</button>
        <div id="annMessage"></div>
    </form>

    <script>
        document.getElementById('commandForm').addEventListener('submit', async function(e) {
            e.preventDefault();
            const cmdMessage = document.getElementById('cmdMessage');
            cmdMessage.textContent = '';
            const command = document.getElementById('command').value.trim();
            const link = document.getElementById('link').value.trim();

            if (!command || !link) {
                cmdMessage.textContent = 'Please fill both fields.';
                cmdMessage.className = 'error';
                return;
            }

            try {
                const res = await fetch('/update', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ command, link })
                });
                const data = await res.json();
                if (res.ok) {
                    cmdMessage.textContent = data.message;
                    cmdMessage.className = 'success';
                    this.reset();
                } else {
                    cmdMessage.textContent = data.error || 'Failed to update command.';
                    cmdMessage.className = 'error';
                }
            } catch (err) {
                cmdMessage.textContent = 'Error: ' + err.message;
                cmdMessage.className = 'error';
            }
        });

        document.getElementById('announcementForm').addEventListener('submit', async function(e) {
            e.preventDefault();
            const annMessage = document.getElementById('annMessage');
            annMessage.textContent = '';
            const announcement = document.getElementById('announcement').value.trim();

            try {
                const res = await fetch('/announcement', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ announcement })
                });
                const data = await res.json();
                if (res.ok) {
                    annMessage.textContent = data.message;
                    annMessage.className = 'success';
                    this.reset();
                } else {
                    annMessage.textContent = data.error || 'Failed to update announcement.';
                    annMessage.className = 'error';
                }
            } catch (err) {
                annMessage.textContent = 'Error: ' + err.message;
                annMessage.className = 'error';
            }
        });
    </script>
</body>
</html>
"""

@app.route("/admin")
def admin_panel():
    result = admin_only()
    if result: return result
    return render_template_string(ADMIN_HTML)

@app.route("/update", methods=["POST"])
def update_command():
    result = admin_only()
    if result: return result
    data = request.json
    if not data or "command" not in data or "link" not in data:
        return jsonify({"error": "Missing 'command' or 'link' in request."}), 400

    command = data["command"].strip().lower()
    link = data["link"].strip()

    with open(COMMANDS_FILE, "r", encoding="utf-8") as file:
        lines = file.readlines()

    updated = False
    for i in range(len(lines)):
        line_cmd = lines[i].split("=", 1)[0].strip().lower()
        if line_cmd == command:
            lines[i] = f"{command}={link}\n"
            updated = True
            break

    if not updated:
        lines.append(f"{command}={link}\n")

    with open(COMMANDS_FILE, "w", encoding="utf-8") as file:
        file.writelines(lines)

    return jsonify({"message": f"Command '{command}' updated successfully."})

@app.route("/announcement", methods=["POST"])
def update_announcement():
    result = admin_only()
    if result: return result
    data = request.json
    if not data or "announcement" not in data:
        return jsonify({"error": "Missing 'announcement' in request."}), 400

    announcement = data["announcement"].strip()

    with open(ANNOUNCEMENT_FILE, "w", encoding="utf-8") as f:
        f.write(announcement if announcement else "No announcements yet.")

    return jsonify({"message": "Announcement updated successfully."})

@app.route("/announcement", methods=["GET"])
def get_announcement():
    if not os.path.exists(ANNOUNCEMENT_FILE):
        return jsonify({"announcement": "No announcements yet."})

    with open(ANNOUNCEMENT_FILE, "r", encoding="utf-8") as f:
        announcement = f.read().strip()
    return jsonify({"announcement": announcement})

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
