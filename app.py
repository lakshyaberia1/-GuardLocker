from ml.generate import generate_password


from flask import Flask, render_template, request, redirect, session, send_file
import os

from crypto_utils import encrypt_file, decrypt_file
from db import init_db, add_user, verify_user

app = Flask(__name__)
app.secret_key = "guardlocker_secret"

UPLOAD_FOLDER = "vault"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

init_db()

@app.route("/")
def home():
    return redirect("/login")

@app.route("/register", methods=["GET","POST"])
def register():
    if request.method == "POST":
        add_user(request.form["username"], request.form["password"])
        return redirect("/login")
    return render_template("register.html")

@app.route("/login", methods=["GET","POST"])
def login():
    if request.method == "POST":
        if verify_user(request.form["username"], request.form["password"]):
            session["user"] = request.form["username"]
            session["password"] = request.form["password"]
            return redirect("/dashboard")
        return "Invalid credentials"
    return render_template("login.html")

@app.route("/dashboard")
def dashboard():
    if "user" not in session:
        return redirect("/login")
    files = os.listdir(UPLOAD_FOLDER)
    return render_template("dashboard.html", files=files)

@app.route("/upload", methods=["POST"])
def upload():
    file = request.files["file"]
    path = os.path.join(UPLOAD_FOLDER, file.filename)
    file.save(path)

    encrypt_file(path, session["password"])

    decoy_password = generate_password(session["password"])

    with open("vault/decoy/decoy_passwords.txt", "a") as f:
        f.write(decoy_password + "\n")

    return redirect("/dashboard")


@app.route("/download/<name>")
def download(name):
    path = os.path.join(UPLOAD_FOLDER, name)
    decrypt_file(path, session["password"])
    return send_file(path, as_attachment=True)

@app.route("/logout")
def logout():
    session.clear()
    return redirect("/login")

if __name__ == "__main__":
    app.run(debug=True)
