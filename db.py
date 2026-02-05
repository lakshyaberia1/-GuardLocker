import sqlite3
import hashlib

DB_NAME = "users.db"

# -------------------------
# Initialize database
# -------------------------
def init_db():
    conn = sqlite3.connect(DB_NAME)
    cur = conn.cursor()

    cur.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE,
            password_hash TEXT
        )
    """)

    conn.commit()
    conn.close()

# -------------------------
# Hash password
# -------------------------
def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

# -------------------------
# Add user
# -------------------------
def add_user(username, password):
    conn = sqlite3.connect(DB_NAME)
    cur = conn.cursor()

    cur.execute(
        "INSERT INTO users (username, password_hash) VALUES (?, ?)",
        (username, hash_password(password))
    )

    conn.commit()
    conn.close()

# -------------------------
# Get user
# -------------------------
def get_user(username):
    conn = sqlite3.connect(DB_NAME)
    cur = conn.cursor()

    cur.execute(
        "SELECT * FROM users WHERE username = ?",
        (username,)
    )

    user = cur.fetchone()
    conn.close()
    return user

# -------------------------
# Verify user
# -------------------------
def verify_user(username, password):
    user = get_user(username)
    if not user:
        return False
    return user[2] == hash_password(password)
