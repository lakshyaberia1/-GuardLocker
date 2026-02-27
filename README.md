# GuardLocker — Honey Password Vault

**Author:** Lakshya Beria, NIELIT
**Version:** 2.0 (Argon2id upgrade)
**Research Base:** Juels & Ristenpart, *Honey Encryption* (EUROCRYPT 2014) · Cheng et al., *Probability Model Transforming Encoders* (USENIX Security 2019) · Cheng et al., *Practically Secure Honey Password Vaults* (USENIX Security 2025)

---

## What is GuardLocker?

GuardLocker is a research prototype of a **honey encryption password vault**. When a wrong master password is entered, the vault does not return a decryption error — it decrypts to a **statistically plausible fake vault**. An attacker who steals the encrypted vault file cannot tell offline whether any given candidate password is correct, because every guess produces valid-looking output.

```
Traditional vault:
  Correct password → Real passwords shown
  Wrong password   → DECRYPTION ERROR  ← attacker instantly knows

GuardLocker:
  Correct password → Real passwords shown
  Wrong password   → Plausible fake vault (attacker cannot distinguish)
```

> **Research prototype notice:** The Transformer model (VaultTransformer) in this repository uses randomly initialised weights. It has not been trained on a password corpus. The honey encryption security guarantees described below depend on a well-trained model; deploying this system in production requires training on an appropriate dataset first.

---

## Project Structure

```
CORE SYSTEM/
├── vault_transformer.py        # Decoder-only Transformer + tokenizer
├── honey_encoder.py            # IS-PMTE encode/decode (honey encryption core)
├── honey_vault_system.py       # Full vault: Argon2id + AES-256-GCM + honey encryption
├── honey_monitor.py            # Async honey account breach monitor
├── requirements.txt            # Python dependencies
└── testing/
    └── RunAllExperiments.py    # Classifier distinguishability experiment
```

---

## Architecture

### 1. VaultTransformer (`vault_transformer.py`)

A decoder-only causal Transformer language model for learning the distribution of real human passwords.

| Parameter | Value |
|---|---|
| Architecture | Decoder-only (TransformerEncoder + causal mask) |
| Hidden dimension | 768 |
| Layers | 12 |
| Attention heads | 12 |
| Feedforward dimension | 3,072 |
| Parameters | ~85 million |
| Vocabulary | 98 tokens (95 printable ASCII + `<SEP>`, `<PAD>`, `<UNK>`) |
| Max sequence length | 1,000 tokens |

The tokenizer handles multi-character special tokens correctly using greedy longest-match before splitting individual characters. Positional encodings use shape `[1, max_len, d_model]` for `batch_first=True` compatibility.

### 2. HoneyEncoder (`honey_encoder.py`)

Implements **IS-PMTE** (Inverse Sampling Probability-Model-Transforming Encoder):

- `encode_vault(passwords)` — maps a list of plaintext passwords to a uniformly distributed byte seed using character-by-character cumulative probability intervals, packed MSB-first.
- `decode_seed(seed)` — maps any byte seed back to a plausible password list by consuming the top bits at each step (MSB-first, matching the encoder).
- `encode_incremental(old_seed, new_password, context)` — appends a new password to an existing vault seed using the prefix-keeping property.

Correct password seed → real vault. Random/wrong seed → statistically plausible decoy vault.

### 3. HoneyVault (`honey_vault_system.py`)

Integrates all components into a complete vault with authenticated encryption.

**Encryption pipeline:**
```
passwords → IS-PMTE encode → seed
{seed_length | seed | vault_json} → AES-256-GCM(Argon2id(master_password, salt)) → ciphertext
```

**Decryption (correct password):**
```
ciphertext → AES-256-GCM decrypt → seed → IS-PMTE decode → real passwords
```

**Decryption (wrong password — AES-GCM authentication fails):**
```
derived_key → seed for deterministic RNG → culturally-calibrated decoy vault
```

**Key derivation — Argon2id (RFC 9106):**

| Parameter | Value |
|---|---|
| Algorithm | Argon2id |
| Time cost (t) | 3 iterations |
| Memory cost (m) | 65,536 KiB (64 MB) |
| Parallelism (p) | 4 threads |
| Output length | 32 bytes (AES-256 key) |
| Salt length | 32 bytes (256-bit, random per vault) |
| Fallback | PBKDF2-HMAC-SHA256 if `argon2-cffi` not installed |

KDF parameters are stored in vault metadata so vaults created with different settings remain readable.

**AES-256-GCM:**
- 96-bit random nonce per encryption
- Full ciphertext authentication (GCM tag covers seed + vault JSON)

**Selective encryption:** Passwords for sites with no effective login rate limiting (`UNLIMITED_LOGIN_SITES`) are stored with cryptographically random 32-character strings instead of honey encryption, preventing cheap online verification by an attacker.

**Culturally-calibrated decoy generator:** Decoys are generated deterministically from the derived key (same wrong password → same decoy, preventing confirmation attacks). The generator is tuned for the Indian user population: Indian first names, family name suffixes, Indian-popular sites (gmail.com, amazon.in, paytm.com, etc.), one consistent primary email identity reused across ~80% of sites, and five empirically observed Indian password patterns (e.g., `rahul2001`, `priya_7342`, common word + digits).

### 4. HoneyAccountMonitor (`honey_monitor.py`)

An async breach detection system that monitors **honey accounts** — fake credentials planted in the vault. If an attacker uses a stolen vault and attempts to log into a honey account, an alert fires immediately.

**Supported monitoring backends:**
- Email IMAP (stub — implementation pending)
- Gmail API (stub — implementation pending)
- GitHub Security Events API (stub — implementation pending)
- HTTP webhook
- Custom callback (sync and async both supported)

**Alert delivery:** SMTP email and/or configurable webhook URL, with per-account cooldown to suppress duplicate alerts.

---

## Installation

**Requirements:** Python 3.10+, PyTorch 2.0+

```bash
cd "CORE SYSTEM"

# Install core dependencies
pip install torch numpy cryptography scikit-learn aiohttp

# Strongly recommended: install Argon2id support
pip install argon2-cffi

# Full dependency set
pip install -r requirements.txt
```

Without `argon2-cffi`, the vault falls back to PBKDF2-HMAC-SHA256 (weaker against GPU attacks). A warning is printed at startup.

---

## Quick Start

```python
from vault_transformer import VaultTransformer, VaultTokenizer
from honey_vault_system import HoneyVault, HoneyAccount
from datetime import datetime

# Initialise system
vault_system = HoneyVault()

# Passwords to store
passwords = [
    {'website': 'github.com',   'username': 'johndoe',          'password': 'MyGitHub2024!'},
    {'website': 'gmail.com',    'username': 'john@example.com', 'password': 'EmailPass123'},
    {'website': 'facebook.com', 'username': 'johndoe',          'password': 'FBSecure456'},
]

# Optional: plant honey accounts for breach detection
honey_accounts = [
    HoneyAccount(
        website='honeytrap.com', username='decoy_user',
        password='HoneyPass1!', created_at=datetime.now()
    ),
]

# Encrypt
master_password = "MySecureMasterPassword123!"
ciphertext, metadata = vault_system.encrypt_vault(passwords, master_password, honey_accounts)

# Correct password → real vault
real_vault = vault_system.decrypt_vault(ciphertext, master_password, metadata)

# Wrong password → plausible fake vault (no error raised)
decoy_vault = vault_system.decrypt_vault(ciphertext, "WrongPassword!", metadata)
```

---

## Honey Account Monitoring

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
    {
        'id': 'honey_1',
        'website': 'github.com',
        'username': 'decoyuser123',
        'password': 'HoneyPass1!',
        'monitoring_service': 'github_api'
    },
]

async def on_breach(alert: BreachAlert):
    print(f"BREACH DETECTED: {alert.website} at {alert.timestamp}")

monitor = HoneyAccountMonitor(config)
asyncio.run(monitor.start_monitoring(honey_accounts, on_breach))
```

> **Note:** The IMAP, Gmail API, and GitHub API monitoring backends are currently stubbed with TODO placeholders. Only the webhook backend is fully functional. Email alerts are sent on detection.

---

## Running the Classifier Experiment

```bash
cd "CORE SYSTEM/testing"
pip install scikit-learn numpy
python "RunAllExperiments·py"
```

This runs the **Decoy Vault Classifier Evaluation** (Experiment 1): generates 5,000 real vaults and 5,000 decoy vaults using a unified site/username/password-pattern pool, extracts 15 structural features, and trains a Random Forest classifier to attempt to distinguish them.

**Expected result after the unified-pool fix:** ~51% classifier accuracy — near the 50% random baseline, which is the target security property of honey encryption.

**Previous broken result (before fix):** ~99–100% accuracy — caused by different site pools for real vs. decoy vaults. The classifier trivially learned site membership (`dropbox.com` only appeared in decoys). This is not a real distinguishability result; it was an experimental bug.

Results are saved to `experiment1_results.json`.

---

## Implementation Bugs Fixed

During development, the following bugs were identified and corrected. Each would have silently broken the system's security or correctness:

| File | Bug | Impact |
|---|---|---|
| `vault_transformer.py` | `TransformerDecoder` used instead of `TransformerEncoder` | Wrong architecture for causal LM |
| `vault_transformer.py` | `PositionalEncoding` shape `[max_len,1,d]` incompatible with `batch_first=True` | Incorrect position at every token |
| `vault_transformer.py` | `VaultTokenizer.encode()` split `<SEP>` into 5 `<UNK>` tokens | Vault boundaries invisible to model |
| `honey_encoder.py` | Encoder packed MSB-first; decoder consumed LSB-first | Passwords decoded in reverse character order |
| `honey_vault_system.py` | `decrypt_vault` reconstructed placeholder `website1.com` / `user1` entries | Website and username lost after encrypt/decrypt |
| `honey_vault_system.py` | `encrypt_vault` mutated caller's input dicts in place | Caller's original passwords silently overwritten |
| `honey_monitor.py` | `asyncio.get_event_loop()` deprecated in Python 3.10+ | Runtime crash on modern Python |
| `honey_monitor.py` | `await alert_callback(alert)` crashed with sync callback | Alert pipeline failed if non-async callback passed |
| `honey_monitor.py` | `vault_model.tokenizer` attribute does not exist on `VaultTransformer` | `AttributeError` in `HoneyAccountGenerator` |
| `RunAllExperiments.py` | Different site pools for real vs. decoy vaults | Classifier got ~100% via site membership — invalid experiment |

---

## Security Properties

| Property | Status |
|---|---|
| Honey encryption (no offline signal on wrong password) | Implemented — security depends on trained model |
| AES-256-GCM authenticated encryption | Implemented |
| Argon2id key derivation (64 MB, 3 iterations) | Implemented (PBKDF2 fallback if argon2-cffi absent) |
| 256-bit random salt per vault | Implemented |
| 96-bit random GCM nonce per encryption | Implemented |
| Culturally-calibrated decoy generation (Indian population) | Implemented |
| Honey accounts for breach detection | Framework implemented; API backends are stubs |
| Transformer vault model (trained) | Architecture implemented; **model not trained** |

---

## Limitations

- **Untrained model:** `VaultTransformer` uses random weights. For real honey encryption security, the model must be trained on a representative password corpus. Decoy plausibility currently relies entirely on the rule-based `_generate_random_decoy_vault()` method.
- **Monitoring backends:** IMAP, Gmail API, and GitHub API backends are not implemented (TODO stubs). Only webhooks and email dispatch are functional.
- **Single experiment:** Only Experiment 1 (classifier distinguishability) is implemented in the test suite. Performance benchmarks and human study evaluation remain future work.
- **Cultural scope:** The decoy generator is calibrated for the Indian user population. Other populations require their own pool construction.

---

## Research References

1. Juels, A. & Ristenpart, T. — *Honey Encryption: Security Beyond the Brute-Force Bound* — EUROCRYPT 2014
2. Cheng, H. et al. — *Probability Model Transforming Encoders Against Encoding Attacks* — USENIX Security 2019
3. Cheng, H. et al. — *Practically Secure Honey Password Vaults* — USENIX Security 2025

---

*Made by Lakshya Beria | NIELIT*