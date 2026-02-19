# 🔒 GuardLocker - Advanced Honey Password Vault

**Protect your passwords with AI-powered honey encryption and instant Telegram alerts!**

## What Makes GuardLocker Special?

Unlike traditional password vaults that **fail** when you enter a wrong master password, GuardLocker **always succeeds** - but generates realistic fake passwords for wrong passwords. This means attackers can't tell if they have the right password without trying to log in online (where you can detect and stop them)!

## 🌟 Key Features

- **🍯 Honey Encryption** - Wrong passwords create realistic decoy vaults
- **🤖 AI-Powered** - 85M parameter Transformer generates plausible fakes
- **📱 Telegram Alerts** - Instant notifications for wrong password attempts
- **🍯 Honey Accounts** - Fake accounts detect if your vault is stolen
- **🔐 Military-Grade Crypto** - AES-256-GCM encryption
- **🌐 Web Interface** - Modern, easy-to-use design
- **📊 Bulk Generation** - Create millions of test passwords

## 🚀 Quick Start (3 Steps!)

### Step 1: Install
```bash
pip install flask flask-cors requests
```

### Step 2: Run
```bash
python web_server_telegram.py
```

### Step 3: Open
Go to `http://localhost:5000` in your browser!

## 📱 Telegram Alerts (Already Set Up!)

Your Telegram bot is **pre-configured** and ready to go! You'll receive alerts for:
- ❌ Wrong password attempts  
- 🚨 Security breaches
- ✅ Important operations

Just start the server and check your Telegram!

## 🎯 How It Works

### Traditional Vault (Vulnerable)
```
Correct Password  → ✅ Real passwords
Wrong Password    → ❌ ERROR! (attacker knows it's wrong)
```

### GuardLocker (Secure)
```
Correct Password  → ✅ Real passwords
Wrong Password 1  → 🎭 Fake vault A (looks real!)
Wrong Password 2  → 🎭 Fake vault B (different fakes!)
```

**Result**: Attacker must verify online → You get Telegram alert → You stop them!

## 📖 Quick Examples

### Create Your First Vault
1. Open `http://localhost:5000`
2. Enter master password (12+ characters)
3. Click "Create New Vault"
4. Start adding passwords!

### Add a Password
1. Enter website (e.g., "github.com")
2. Enter username
3. Enter password (or generate one!)
4. Click "Save Password"

### Test Security
1. Lock your vault
2. Try a **wrong** master password
3. See realistic fake passwords!
4. Check Telegram - you got an alert!

## 🔒 Security Features

### 1. Honey Encryption
- ANY password works (even wrong ones!)
- Wrong passwords → Realistic fakes
- Attacker can't tell offline
- Forces online verification (you detect this!)

### 2. Honey Accounts  
- 10-20 fake accounts mixed with real ones
- If anyone logs in → Instant Telegram alert!
- Detects if your vault was stolen

### 3. Telegram Monitoring
```
🚨 UNAUTHORIZED ACCESS ATTEMPT #3

⏰ Time: 2026-02-19 15:30:45
🔐 Wrong password entered
📊 Failed attempts: 3

⚠️ Action Required:
- Check if this was you
- Change master password if suspicious
```

## 📚 Files Included

- `README.md` - This file (quick start guide)
- `USER_MANUAL.md` - Detailed instructions
- `web_server_telegram.py` - Main server with Telegram
- `honey_vault_system_fixed.py` - Fixed honey vault
- `test_honey_vault.py` - Test script (no ML needed!)
- `FIX_GUIDE.md` - Troubleshooting

## ⚡ Performance

- **Fast**: Encrypt 20 passwords in ~1-2 seconds
- **Light**: Only 326MB model (can compress to 82MB)
- **Works on**: Desktop, laptop, even mobile!

## 🐛 Troubleshooting

### Server won't start?
```bash
python3 --version  # Check Python 3.11+
pip install flask flask-cors requests
python web_server_telegram.py
```

### No Telegram alerts?
Check `web_server_telegram.py` has your credentials:
```python
TELEGRAM_BOT_TOKEN = "8343225909:AAEaWkZx-FM6-LqKjbnUsfSdvxUTCGsp2NA"
TELEGRAM_CHAT_ID = "5590835443"
```

### Wrong password opens same vault?
Use the **FIXED** version: `honey_vault_system_fixed.py`

Test it:
```bash
python test_honey_vault.py
```

Should show:
```
✅ CORRECT PASSWORD - All passwords match!
✅ WRONG PASSWORD #1 - No real passwords leaked
✅ WRONG PASSWORD #2 - Different decoys!
```

## 🔬 Research Credit

Based on cutting-edge research from:
> "Practically Secure Honey Password Vaults"  
> Cheng et al., USENIX Security 2025

**Security Results**:
- Traditional vaults: 0.76 accounts hacked per 1,000 tries
- GuardLocker: 0.05 accounts hacked per 1,000 tries
- **15x more secure!**

## 📖 Need More Help?

See `USER_MANUAL.md` for:
- Detailed step-by-step instructions
- Screenshots and examples
- Advanced features
- Security best practices
- Common issues and solutions

## 🎉 You're Ready!

Start the server and protect your passwords now:
```bash
python web_server_telegram.py
```

Then open: `http://localhost:5000`

You'll receive Telegram alerts automatically! 🔔

---

**Made with ❤️ by Lakshya Beria and Danish| Based on research by Haibo Cheng et al.**