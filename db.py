import sqlite3
import os
import hashlib

DB_NAME = "users.db"

# -------------------------
# Initialize Database
# -------------------------
def init_db():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE,
            password_hash TEXT
        )
    """)

    conn.commit()
    conn.close()

# -------------------------
# Hash Password
# -------------------------
def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

# -------------------------
# Add User
# -------------------------
def add_user(username, password):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()

    cursor.execute(
        "INSERT INTO users (username, password_hash) VALUES (?, ?)",
        (username, hash_password(password))
    )

    conn.commit()
    conn.close()

# -------------------------
# Get User
# -------------------------
def get_user(username):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()

    cursor.execute(
        "SELECT * FROM users WHERE username = ?",
        (username,)
    )

    user = cursor.fetchone()
    conn.close()
    return user

# -------------------------
# Verify User
# -------------------------
def verify_user(username, password):
    user = get_user(username)

    if not user:
        return False

    return user[2] == hash_password(password)
