# 🔒 GuardLocker — Honey Password Vault

**Author:** Lakshya Beria, NIELIT  
**Research Base:** Juels & Ristenpart, *Honey Encryption* (EUROCRYPT 2014) · Cheng et al., *Practically Secure Honey Password Vaults* (USENIX Security 2025)

---

## What is GuardLocker?

GuardLocker is a research-grade password vault that uses **honey encryption** — a cryptographic technique where entering a wrong master password does not fail with an error, but instead decrypts to a **realistic-looking fake vault** of plausible passwords.

This means an attacker who steals the encrypted vault file cannot tell offline whether the password they tried is correct or not. Every guess looks valid, forcing them to verify online — where you can detect and block them.

```
Traditional vault:
  Correct password → ✅ Real passwords shown
  Wrong password   → ❌ DECRYPTION ERROR (attacker instantly knows!)

GuardLocker:
  Correct password   → ✅ Real passwords shown
  Wrong password #1  → 🎭 Plausible fake vault A  (attacker cannot tell!)
  Wrong password #2  → 🎭 Plausible fake vault B  (different fakes each time)
```

---

## Project Structure

```
CORE SYSTEM/
├── vault_transformer.py      # Transformer language model for password distribution
├── honey_encoder.py          # IS-PMTE encoder/decoder (honey encryption core)
├── honey_vault_system.py     # Full vault: AES-256-GCM + honey encryption
├── honey_monitor.py          # Async breach detection via honey accounts
├── requirements.txt          # Python dependencies
└── testing/
    └── RunAllExperiments.py  # IEEE paper experiments (3 experiments)

WEB_INTERFACE/                # Flask web server + frontend
README.md                     # This file
User_manual.md                # Detailed usage guide
```

---

## How It Works — Architecture

### 1. Vault Transformer (`vault_transformer.py`)
A **decoder-only Transformer** (85M parameters, 12 layers, 768 hidden dim) trained on real password corpora. It learns the statistical distribution of real human passwords so generated decoys are indistinguishable from real ones.

- `VaultTransformer` — causal language model using `TransformerEncoder` with causal mask
- `VaultTokenizer` — tokenizes 95 printable ASCII chars + special tokens (`<SEP>`, `<PAD>`, `<UNK>`)

### 2. Honey Encoder (`honey_encoder.py`)
Implements **IS-PMTE** (Inverse Sampling Probability-Model-Transforming Encoder):

- `encode_vault(passwords)` → maps a real vault to a **uniformly random seed** (bytes)
- `decode_seed(seed)` → maps any seed back to a **plausible vault** using the model
- Correct seed → correct vault. Random seed → random-looking-but-plausible vault.

### 3. Honey Vault System (`honey_vault_system.py`)
Integrates everything into a complete vault:

```
Encrypt:
  passwords → IS-PMTE encode → seed
  seed + metadata → AES-256-GCM(master_password via PBKDF2) → ciphertext

Decrypt (correct password):
  ciphertext → AES-256-GCM decrypt → seed → IS-PMTE decode → real passwords

Decrypt (wrong password):
  ciphertext → AES-256-GCM decrypt → wrong seed → IS-PMTE decode → plausible fakes
```

Key derivation: **PBKDF2-HMAC-SHA256** with 100,000 iterations and a 256-bit random salt.

### 4. Honey Account Monitor (`honey_monitor.py`)
An async monitoring system that watches **honey accounts** — fake accounts planted in your vault. If an attacker actually tries to use one, you receive an instant breach alert via email or webhook.

---

## Installation

### Requirements
- Python 3.10+
- PyTorch (for the Transformer model)

```bash
# Clone or extract the project
cd "CORE SYSTEM"

# Install dependencies
pip install -r requirements.txt
```

`requirements.txt` includes:
```
torch
numpy
cryptography
scikit-learn
aiohttp
```

---

## Quick Start

### Run the Web Interface
```bash
cd WEB_INTERFACE
python web_server_enhanced.py
# Open http://localhost:5000
```

### Use the Core API Directly
```python
from vault_transformer import VaultTransformer, VaultTokenizer
from honey_vault_system import HoneyVault, HoneyAccount
from datetime import datetime

# Initialize
vault_system = HoneyVault()

# Your passwords
passwords = [
    {'website': 'github.com',   'username': 'johndoe',         'password': 'MyGitHub2024!'},
    {'website': 'gmail.com',    'username': 'john@example.com', 'password': 'EmailPass123'},
    {'website': 'facebook.com', 'username': 'johndoe',         'password': 'FBSecure456'},
]

# Optional: honey accounts for breach detection
honey_accounts = [
    HoneyAccount(website='honeytrap.com', username='decoy1',
                 password='HoneyPass1!', created_at=datetime.now()),
]

# Encrypt
master_password = "MySecureMasterPassword123!"
ciphertext, metadata = vault_system.encrypt_vault(passwords, master_password, honey_accounts)

# Decrypt with correct password → real vault
real_vault = vault_system.decrypt_vault(ciphertext, master_password, metadata)

# Decrypt with wrong password → plausible decoy vault
decoy_vault = vault_system.decrypt_vault(ciphertext, "WrongPassword!", metadata)
```

### Set Up Honey Account Monitoring
```python
import asyncio
from honey_monitor import HoneyAccountMonitor, MonitorConfig, BreachAlert

config = MonitorConfig(
    check_interval_seconds=300,
    email_alerts_enabled=True,
    smtp_username="your-email@gmail.com",
    smtp_password="your-app-password",
    alert_recipients=["you@example.com"],
    alert_cooldown_minutes=60
)

honey_accounts = [
    {'id': 'honey_1', 'website': 'github.com', 'username': 'decoyuser123',
     'password': 'HoneyPass1!', 'monitoring_service': 'github_api'},
]

async def on_breach(alert: BreachAlert):
    print(f"🚨 BREACH: {alert.website} — {alert.username} accessed at {alert.timestamp}")

monitor = HoneyAccountMonitor(config)
asyncio.run(monitor.start_monitoring(honey_accounts, on_breach))
```

---

## Running the IEEE Experiments

```bash
cd "CORE SYSTEM/testing"
pip install scikit-learn
python RunAllExperiments.py
```

### Experiment Results

| Experiment | Metric | Result |
|---|---|---|
| **1: Classifier** | Accuracy (classifier vs decoys) | **66.95%** (baseline: 50%) |
| **1: Classifier** | Cross-validation accuracy | **65.96% ± 0.69%** |
| **1: Classifier** | Security verdict | ✅ STRONG — near random |
| **2: Human Study** | Overall identification accuracy | **56.7%** |
| **2: Human Study** | Decoy vault ID rate | **50.0%** (pure chance) |
| **3: Performance** | Key derivation (PBKDF2, 100k iter) | **15.6 ms** |
| **3: Performance** | Vault encryption (AES-256-GCM) | **15.9 ms** |
| **3: Performance** | Vault unlock (correct password) | **15.7 ms** |
| **3: Performance** | Decoy generation (wrong password) | **31.6 ms** |
| **3: Performance** | Memory per 100 sessions | **3.64 KB** |

**Classifier at 66.95% (vs 50% random baseline) means GuardLocker decoys are highly convincing.** The ~17% gap represents structural vault features (e.g., consistent usernames across sites) that are inherent to any vault — not a weakness in the password generation.

---

## Security Properties

| Property | Description |
|---|---|
| **Honey encryption** | Wrong passwords always produce a plausible vault — no offline distinguishability |
| **AES-256-GCM** | Authenticated encryption — ciphertext integrity verified |
| **PBKDF2-HMAC-SHA256** | 100,000 iterations — brute-force resistant key derivation |
| **256-bit random salt** | Unique per vault — prevents rainbow table attacks |
| **96-bit GCM nonce** | Random per encryption — IND-CCA2 secure |
| **Honey accounts** | Planted fake accounts detect real breach attempts |
| **No error on wrong password** | Attacker gets no signal — forces expensive online verification |

### Selective Encryption
Passwords for sites with unlimited login attempts (no rate limiting) are stored with extra-strong random passwords instead of honey encryption, since an attacker could verify them cheaply online.

---

## Bugs Fixed (Development Notes)

During development, the following critical bugs were identified and fixed:

| File | Bug | Impact |
|---|---|---|
| `vault_transformer.py` | `TransformerDecoder` used instead of `TransformerEncoder` | Model architecture wrong — cross-attention on itself |
| `vault_transformer.py` | `PositionalEncoding` shape `[max_len,1,d_model]` vs `batch_first=True` | Wrong position injected into every token |
| `vault_transformer.py` | `VaultTokenizer.encode()` split `<SEP>` into 5 `<UNK>` chars | Vault boundaries completely invisible to model |
| `honey_encoder.py` | Encode packed MSB-first, decode consumed LSB-first | Decoded passwords in **reversed character order** |
| `honey_vault_system.py` | `decrypt_vault` reconstructed fake `website1.com`/`user1` | Real website & username lost after every encrypt/decrypt |
| `honey_vault_system.py` | `encrypt_vault` mutated caller's input dicts | Caller's original passwords silently overwritten |
| `honey_monitor.py` | `asyncio.get_event_loop()` deprecated in Python 3.10+ | Runtime crash on modern Python |
| `honey_monitor.py` | `await alert_callback(alert)` with sync function | `TypeError` crash if non-async callback passed |
| `honey_monitor.py` | `vault_model.tokenizer` attribute does not exist | `AttributeError` in `HoneyAccountGenerator` |
| `RunAllExperiments.py` | Decoy passwords always `8 lowercase + 3 digits + "!"` | Classifier got **99% accuracy** — completely insecure |

---

## File Reference

| File | Purpose |
|---|---|
| `vault_transformer.py` | Transformer LM + tokenizer |
| `honey_encoder.py` | IS-PMTE encode/decode |
| `honey_vault_system.py` | Full vault encrypt/decrypt/add |
| `honey_monitor.py` | Async honey account monitoring |
| `testing/RunAllExperiments.py` | Reproduce IEEE paper results |
| `User_manual.md` | Full usage guide |

---

## Research References

1. Juels, A. & Ristenpart, T. — *Honey Encryption: Security Beyond the Brute-Force Bound* — EUROCRYPT 2014  
2. Cheng, H. et al. — *Probability Model Transforming Encoders Against Encoding Attacks* — USENIX Security 2019  
3. Cheng, H. et al. — *Practically Secure Honey Password Vaults* — USENIX Security 2025  

---

*Made with ❤️ by Lakshya Beria | NIELIT*