from flask import Flask, render_template, request, redirect, session, send_file
import os

from crypto_utils import encrypt_file, decrypt_file
from db import init_db, add_user, get_user, verify_user

app = Flask(__name__)
app.secret_key = "guardlocker_secret"

UPLOAD_FOLDER = "vault/real"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# Initialize DB
init_db()

# -------------------------
# Home
# -------------------------
@app.route("/")
def home():
    return redirect("/login")

# -------------------------
# Register
# -------------------------
@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]

        add_user(username, password)
        return redirect("/login")

    return render_template("register.html")

# -------------------------
# Login
# -------------------------
@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]

        if verify_user(username, password):
            session["user"] = username
            session["password"] = password
            return redirect("/dashboard")
        else:
            return "Invalid credentials"

    return render_template("login.html")

# -------------------------
# Dashboard
# -------------------------
@app.route("/dashboard")
def dashboard():
    if "user" not in session:
        return redirect("/login")

    files = os.listdir(UPLOAD_FOLDER)
    return render_template("dashboard.html", files=files)

# -------------------------
# Upload File
# -------------------------
@app.route("/upload", methods=["POST"])
def upload():
    if "user" not in session:
        return redirect("/login")

    file = request.files["file"]
    file_path = os.path.join(UPLOAD_FOLDER, file.filename)
    file.save(file_path)

    encrypt_file(file_path, session["password"])

    return redirect("/dashboard")

# -------------------------
# Download File
# -------------------------
@app.route("/download/<filename>")
def download(filename):
    if "user" not in session:
        return redirect("/login")

    file_path = os.path.join(UPLOAD_FOLDER, filename)

    decrypt_file(file_path, session["password"])

    return send_file(file_path, as_attachment=True)

# -------------------------
# Logout
# -------------------------
@app.route("/logout")
def logout():
    session.clear()
    return redirect("/login")

# -------------------------
if __name__ == "__main__":
    app.run(debug=True)
