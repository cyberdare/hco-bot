from flask import Flask, render_template, request, redirect, url_for, session, jsonify, render_template_string
from werkzeug.security import generate_password_hash, check_password_hash
import os
import sqlite3

app = Flask(__name__)
app.secret_key = 'your_secret_key'

DB_FILE = 'users.db'
COMMANDS_FILE = 'commands.txt'
ANNOUNCEMENT_FILE = 'announcement.txt'
DIRECT_COMMANDS_FILE = 'directcommands.txt'

ADMIN_USERS = {
    "ashish": generate_password_hash("welcome2025"),
    "Dare": generate_password_hash("Dare@3456789")
}

def init_db():
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("""CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE,
        password TEXT
    )""")
    conn.commit()
    conn.close()

init_db()

# Ensure essential files
for file in [COMMANDS_FILE, ANNOUNCEMENT_FILE, DIRECT_COMMANDS_FILE]:
    if not os.path.exists(file):
        with open(file, "w", encoding="utf-8") as f:
            if file == ANNOUNCEMENT_FILE:
                f.write("No announcements yet.")

@app.route("/")
def index():
    return redirect(url_for('login'))

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]

        if username in ADMIN_USERS and check_password_hash(ADMIN_USERS[username], password):
            session["username"] = username
            session["is_admin"] = True
            return redirect(url_for("admin_panel"))

        conn = sqlite3.connect(DB_FILE)
        c = conn.cursor()
        c.execute("SELECT password FROM users WHERE username = ?", (username,))
        result = c.fetchone()
        conn.close()
        if result and check_password_hash(result[0], password):
            session["username"] = username
            session["is_admin"] = False
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
    if "username" not in session or session.get("is_admin"):
        return redirect(url_for("login"))
    return render_template("chatbot.html", username=session["username"])

@app.route("/commands")
def commands():
    with open(COMMANDS_FILE, "r", encoding="utf-8") as f:
        lines = [line.strip() for line in f if '=' in line]
    return jsonify({"commands": lines})

@app.route("/directcommands")
def direct_commands():
    with open(DIRECT_COMMANDS_FILE, "r", encoding="utf-8") as f:
        lines = [line.strip() for line in f if '=' in line]
    return jsonify({"directcommands": lines})

@app.route("/logout")
def logout():
    session.pop("username", None)
    session.pop("is_admin", None)
    return redirect(url_for("login"))

def admin_only():
    if not session.get("is_admin"):
        return redirect(url_for("login"))

# ========== ADMIN PANEL ==========
ADMIN_HTML = """
<!DOCTYPE html>
<html>
<head><meta charset='UTF-8'><title>Admin Panel</title>
<style>
body { font-family: Arial; background: #111; color: #eee; padding: 20px; }
h1 { color: #0f0; }
label { display: block; margin-top: 10px; }
input, textarea {
  width: 100%; background: #222; color: #fff; border: none;
  padding: 8px; border-radius: 4px; margin-top: 5px;
}
button {
  margin-top: 15px; background: #0f0; color: #000; padding: 10px 20px;
  border: none; border-radius: 4px; cursor: pointer;
}
.success { color: #0f0; margin-top: 10px; }
.error { color: #f33; margin-top: 10px; }
</style></head>
<body>
<h1>Hackers Colony Admin Panel</h1>

<form id="commandForm">
  <label>Video Command Name:</label>
  <input type="text" id="command" required>
  <label>Video Link:</label>
  <input type="text" id="link" required>
  <button type="submit">Save Video Command</button>
  <div id="cmdMessage"></div>
</form>

<form id="announcementForm">
  <label>Announcement:</label>
  <textarea id="announcement" rows="4"></textarea>
  <button type="submit">Save Announcement</button>
  <div id="annMessage"></div>
</form>

<form id="directCommandForm">
  <label>Tool Name:</label>
  <input type="text" id="dcommand" required>
  <label>Tool Commands (multi-line):</label>
  <textarea id="dlink" rows="6" required></textarea>
  <button type="submit">Save Direct Command</button>
  <div id="dCmdMessage"></div>
</form>

<script>
async function handleForm(id, url, fields, msgId) {
  document.getElementById(id).addEventListener('submit', async e => {
    e.preventDefault();
    const data = {};
    fields.forEach(f => data[f] = document.getElementById(f).value.trim());
    if (id === 'directCommandForm') data['value'] = data['dlink'].replace(/\\n/g, '\\\\n');
    const res = await fetch(url, {
      method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(data)
    });
    const json = await res.json();
    const el = document.getElementById(msgId);
    el.textContent = json.message || json.error || 'Failed';
    el.className = res.ok ? 'success' : 'error';
    if (res.ok) document.getElementById(id).reset();
  });
}
handleForm('commandForm', '/update', ['command', 'link'], 'cmdMessage');
handleForm('announcementForm', '/announcement', ['announcement'], 'annMessage');
handleForm('directCommandForm', '/directupdate', ['dcommand', 'dlink'], 'dCmdMessage');
</script>
</body></html>
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
    command, link = data["command"].strip().lower(), data["link"].strip()
    updated = False
    lines = []
    if os.path.exists(COMMANDS_FILE):
        with open(COMMANDS_FILE, "r", encoding="utf-8") as f:
            lines = f.readlines()
        for i, line in enumerate(lines):
            if line.split("=")[0].strip().lower() == command:
                lines[i] = f"{command}={link}\n"
                updated = True
                break
    if not updated:
        lines.append(f"{command}={link}\n")
    with open(COMMANDS_FILE, "w", encoding="utf-8") as f:
        f.writelines(lines)
    return jsonify({"message": f"Command '{command}' saved."})

@app.route("/directupdate", methods=["POST"])
def update_direct_command():
    result = admin_only()
    if result: return result
    data = request.json
    name, value = data["dcommand"].strip().lower(), data["value"].strip()
    updated = False
    lines = []
    if os.path.exists(DIRECT_COMMANDS_FILE):
        with open(DIRECT_COMMANDS_FILE, "r", encoding="utf-8") as f:
            lines = f.readlines()
        for i, line in enumerate(lines):
            if line.split("=")[0].strip().lower() == name:
                lines[i] = f"{name}={value}\n"
                updated = True
                break
    if not updated:
        lines.append(f"{name}={value}\n")
    with open(DIRECT_COMMANDS_FILE, "w", encoding="utf-8") as f:
        f.writelines(lines)
    return jsonify({"message": f"Direct command '{name}' saved."})

@app.route("/announcement", methods=["POST"])
def update_announcement():
    result = admin_only()
    if result: return result
    text = request.json.get("announcement", "").strip()
    with open(ANNOUNCEMENT_FILE, "w", encoding="utf-8") as f:
        f.write(text if text else "No announcements yet.")
    return jsonify({"message": "Announcement updated."})

@app.route("/announcement", methods=["GET"])
def get_announcement():
    if not os.path.exists(ANNOUNCEMENT_FILE):
        return jsonify({"announcement": "No announcements yet."})
    with open(ANNOUNCEMENT_FILE, "r", encoding="utf-8") as f:
        return jsonify({"announcement": f.read().strip()})

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
