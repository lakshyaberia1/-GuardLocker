# DecoyVault

**A secure personal file vault with encryption, decoy mode, local network sharing, and cloud backup**

DecoyVault is a simple, privacy-focused web app that lets you store sensitive files safely on your computer. Files are encrypted so no one can read them without your password. It includes a clever "decoy mode" that shows fake files if someone enters the wrong password (great for protection in shared spaces like college hostels). You can also share files securely over your local Wi-Fi and backup everything to the cloud.

Built for the ED Fest project showcase (NIELIT visitors, February 2026).

## Features
- **Strong Encryption**: Files are locked using AES-256 encryption (Fernet from cryptography library).
- **Decoy Mode**: Wrong password shows fake harmless files to fool snoopers.
- **Web Interface**: Easy to use in your browser (upload, download, list files).
- **Secure Local Sharing**: Send encrypted files to friends on the same Wi-Fi (no internet needed).
- **Cloud Backup**: Automatic or manual backup of encrypted vault to AWS S3 (or similar).
- **Alerts**: Get Telegram notifications on failed login attempts.
- **Runs on Linux**: Lightweight and works on any laptop/PC with Python.

## Why This Project?
In places like Delhi hostels or shared computers, files can be stolen or peeked at. DecoyVault solves this by:
- Keeping everything encrypted locally.
- Tricking unauthorized users with fake data.
- Allowing safe sharing without risky apps like WhatsApp.
- Protecting against data loss with encrypted cloud backups.

Perfect for students, freelancers, or anyone handling private documents (resumes, notes, photos, etc.).

## Tech Stack
- **Backend**: Python + FastAPI (modern and fast web framework)
- **Encryption**: cryptography library (Fernet for AES-256)
- **Frontend**: Simple HTML + Bootstrap (via CDN)
- **Networking**: Python sockets for local Wi-Fi discovery and file transfer
- **Cloud**: boto3 for AWS S3 backup
- **Alerts**: python-telegram-bot (optional)
- **Environment**: Linux (tested on Ubuntu)

No heavy dependencies — everything installs with pip.

## Installation & Setup

### Prerequisites
- Python 3.8+ (most Linux comes with it)
- pip (Python package manager)
- Git (optional, for cloning)

### Step 1: Clone or Create Project
```bash
git clone https://github.com/yourusername/decoyvault.git
# OR just make a folder
mkdir decoyvault
cd decoyvault# DecoyVault

**A secure personal file vault with encryption, decoy mode, local network sharing, and cloud backup**

DecoyVault is a simple, privacy-focused web app that lets you store sensitive files safely on your computer. Files are encrypted so no one can read them without your password. It includes a clever "decoy mode" that shows fake files if someone enters the wrong password (great for protection in shared spaces like college hostels). You can also share files securely over your local Wi-Fi and backup everything to the cloud.

Built for the ED Fest project showcase (NIELIT visitors, February 2026).

## Features
- **Strong Encryption**: Files are locked using AES-256 encryption (Fernet from cryptography library).
- **Decoy Mode**: Wrong password shows fake harmless files to fool snoopers.
- **Web Interface**: Easy to use in your browser (upload, download, list files).
- **Secure Local Sharing**: Send encrypted files to friends on the same Wi-Fi (no internet needed).
- **Cloud Backup**: Automatic or manual backup of encrypted vault to AWS S3 (or similar).
- **Alerts**: Get Telegram notifications on failed login attempts.
- **Runs on Linux**: Lightweight and works on any laptop/PC with Python.

## Why This Project?
In places like Delhi hostels or shared computers, files can be stolen or peeked at. DecoyVault solves this by:
- Keeping everything encrypted locally.
- Tricking unauthorized users with fake data.
- Allowing safe sharing without risky apps like WhatsApp.
- Protecting against data loss with encrypted cloud backups.

Perfect for students, freelancers, or anyone handling private documents (resumes, notes, photos, etc.).

## Tech Stack
- **Backend**: Python + FastAPI (modern and fast web framework)
- **Encryption**: cryptography library (Fernet for AES-256)
- **Frontend**: Simple HTML + Bootstrap (via CDN)
- **Networking**: Python sockets for local Wi-Fi discovery and file transfer
- **Cloud**: boto3 for AWS S3 backup
- **Alerts**: python-telegram-bot (optional)
- **Environment**: Linux (tested on Ubuntu)

No heavy dependencies — everything installs with pip.

## Installation & Setup

### Prerequisites
- Python 3.8+ (most Linux comes with it)
- pip (Python package manager)
- Git (optional, for cloning)

### Step 1: Clone or Create Project
```bash
git clone https://github.com/yourusername/decoyvault.git
# OR just make a folder
mkdir decoyvault
cd decoyvault
Step 2: Set Up Virtual Environment
Bashpython3 -m venv myenv
source myenv/bin/activate
Step 3: Install Dependencies
Bashpip install fastapi uvicorn cryptography python-dotenv boto3 python-telegram-bot
Step 4: Create .env File
Create a file named .env in the project root:
envMASTER_PASSWORD=your_very_strong_password_here   # Change this!
TELEGRAM_TOKEN=your_telegram_bot_token           # Optional
TELEGRAM_CHAT_ID=your_chat_id                    # Optional
AWS_ACCESS_KEY_ID=your_aws_key                   # For cloud backup
AWS_SECRET_ACCESS_KEY=your_aws_secret
S3_BUCKET_NAME=your-bucket-name
Never commit .env to Git! Add .env to .gitignore.
Step 5: Create Folders
Bashmkdir vault decoy
# Add some fake files in decoy/ (e.g. echo "This is fake" > decoy/fake_note.txt)
Step 6: Run the App
Bashuvicorn app:app --reload --host 0.0.0.0
Open your browser: http://localhost:8000 (or your IP if on network)
For docs and testing: http://localhost:8000/docs
How to Use (Quick Demo Guide)

Go to the login page → enter your MASTER_PASSWORD.
Upload a file → it gets encrypted and saved in vault/.
Try wrong password 3 times → decoy mode shows fake files.
Share: Use the share button to send to another device on same Wi-Fi.
Backup: Hit the backup button → encrypted zip goes to cloud.

Project Structure
textdecoyvault/
├── app.py              # Main FastAPI application
├── .env                # Secrets (do NOT share!)
├── vault/              # Encrypted real files
├── decoy/              # Fake files for decoy mode
├── README.md           # This file
└── myenv/              # Virtual environment (ignore in Git)
Future Improvements (Ideas)

Add user registration (multiple users).
Mobile-friendly UI.
Better file preview (images, PDFs).
Password change feature.
Auto-lock after inactivity.

Security Notes

All encryption happens locally — nothing sent in plain text.
Use a strong, unique MASTER_PASSWORD.
For production: Use HTTPS (self-signed cert with mkcert) and proper rate limiting.
This is a student project — not audited for high-security use.

License
MIT License — free to use, modify, and share for learning.
Made with ❤️ by Lakshya (Delhi) for ED Fest 2026.
Questions? Reach out or open an issue!
Happy securing! 🔒
text### How to Use This README
1. Create the file: In your project folder, type `nano README.md`, paste the content above, save (Ctrl+O → Enter → Ctrl+X).
2. Customize:
   - Change name if you want (search/replace "DecoyVault").
   - Add your GitHub link if you upload to GitHub.
   - Update dates or add screenshots later (e.g., `![Demo](screenshot.png)`).
3. Push to GitHub (optional but recommended for fest): `git init`, `git add .`, `git commit -m "Initial commit"`, create repo on GitHub, then push.

This README is clean, explains everything simply (since you're new), and shows professionalism. It will help during your demo too — you can point to sections.

If you want to add screenshots, change name, or make it shor
