import os
import base64
import hashlib
from cryptography.fernet import Fernet

# Generate encryption key from password
def generate_key(password: str) -> bytes:
    hashed = hashlib.sha256(password.encode()).digest()
    return base64.urlsafe_b64encode(hashed)

# Encrypt file
def encrypt_file(file_path, password):
    key = generate_key(password)
    fernet = Fernet(key)

    with open(file_path, "rb") as file:
        data = file.read()

    encrypted_data = fernet.encrypt(data)

    with open(file_path, "wb") as file:
        file.write(encrypted_data)

# Decrypt file
def decrypt_file(file_path, password):
    key = generate_key(password)
    fernet = Fernet(key)

    with open(file_path, "rb") as file:
        encrypted_data = file.read()

    decrypted_data = fernet.decrypt(encrypted_data)

    with open(file_path, "wb") as file:
        file.write(decrypted_data)
