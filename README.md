# GuardLocker - Advanced Honey Password Vault

## 🔒 Next-Generation Password Security

GuardLocker is a state-of-the-art password vault implementing **Honey Encryption** technology based on cutting-edge research from USENIX Security 2025. It provides **information-theoretic security** against offline attacks while maintaining practical usability.

### 🌟 Key Features

- **🍯 Honey Encryption**: Generates plausible decoy vaults for incorrect master passwords
- **🤖 AI-Powered**: Transformer-based model (85M parameters) for realistic password generation
- **🔍 Breach Detection**: Honey accounts automatically detect vault compromises
- **🛡️ Defense in Depth**: Multiple security layers including selective encryption
- **⚡ Efficient**: Optimized with ONNX for fast encryption/decryption
- **🔐 Zero-Knowledge**: Client-side encryption ensures server never sees passwords

---

## 📋 Table of Contents

1. [Architecture](#architecture)
2. [Installation](#installation)
3. [Quick Start](#quick-start)
4. [Security Features](#security-features)
5. [Training Your Own Model](#training-your-own-model)
6. [API Reference](#api-reference)
7. [Advanced Configuration](#advanced-configuration)
8. [Performance](#performance)
9. [Security Considerations](#security-considerations)
10. [Contributing](#contributing)
11. [Research Background](#research-background)

---

## 🏗️ Architecture

### System Overview

```
┌─────────────────────────────────────────────────────────────┐
│                     GuardLocker System                      │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  ┌──────────────┐      ┌──────────────┐                    │
│  │   User UI    │──────│  Vault API   │                    │
│  └──────────────┘      └──────────────┘                    │
│                              │                              │
│         ┌────────────────────┼────────────────────┐        │
│         │                    │                    │        │
│  ┌──────▼──────┐   ┌─────────▼────────┐  ┌───────▼──────┐ │
│  │ Transformer │   │  Honey Encoder   │  │  AES-256-GCM │ │
│  │   Model     │   │    (IS-PMTE)     │  │  Encryption  │ │
│  │  (85M params)│   │                  │  │              │ │
│  └─────────────┘   └──────────────────┘  └──────────────┘ │
│                                                             │
│  ┌──────────────────────────────────────────────────────┐  │
│  │         Honey Account Monitoring System              │  │
│  │  - Email monitoring  - API integration               │  │
│  │  - Webhook alerts    - Breach detection              │  │
│  └──────────────────────────────────────────────────────┘  │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

### Data Flow

1. **Encryption**:
   ```
   Passwords → Transformer Model → Seed → AES Encryption → Ciphertext
   ```

2. **Decryption (Correct Password)**:
   ```
   Ciphertext → AES Decryption → Seed → Decoder → Real Passwords
   ```

3. **Decryption (Incorrect Password)**:
   ```
   Ciphertext → AES Decryption → Random Seed → Decoder → Decoy Passwords
   ```

---

## 💻 Installation

### Prerequisites

- Python 3.11 or higher
- CUDA 11.8+ (optional, for GPU acceleration)
- 8GB RAM minimum (16GB recommended)
- 2GB disk space for models

### Install from Source

```bash
# Clone repository
git clone https://github.com/your-username/guardlocker.git
cd guardlocker

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Optional: Install with GPU support
pip install torch torchvision --index-url https://download.pytorch.org/whl/cu118
```

### Docker Installation (Recommended)

```bash
# Build Docker image
docker build -t guardlocker:latest .

# Run container
docker run -p 8000:8000 -v $(pwd)/data:/data guardlocker:latest
```

---

## 🚀 Quick Start

### 1. Basic Usage

```python
from honey_vault_system import HoneyVault
from vault_transformer import VaultTransformer, VaultTokenizer

# Initialize system
vault_system = HoneyVault()

# Create password vault
passwords = [
    {'website': 'github.com', 'username': 'user', 'password': 'MyGitHub2024!'},
    {'website': 'gmail.com', 'username': 'user@gmail.com', 'password': 'EmailPass123'},
]

master_password = "MySecureMasterPassword123!"

# Encrypt vault
ciphertext, metadata = vault_system.encrypt_vault(
    passwords,
    master_password
)

print(f"Vault encrypted! Size: {len(ciphertext)} bytes")

# Decrypt with correct password
decrypted = vault_system.decrypt_vault(ciphertext, master_password, metadata)
print(f"Decrypted {len(decrypted)} passwords")

# Decrypt with WRONG password (generates plausible decoys)
wrong_password = "WrongPassword123!"
decoy_vault = vault_system.decrypt_vault(ciphertext, wrong_password, metadata)
print(f"Decoy vault: {decoy_vault}")  # Looks real but isn't!
```

### 2. With Honey Accounts (Breach Detection)

```python
from honey_monitor import HoneyAccountGenerator, HoneyAccountMonitor, MonitorConfig
from datetime import datetime

# Generate honey accounts
generator = HoneyAccountGenerator(vault_system.model)
honey_accounts = generator.generate_honey_accounts(count=10)

# Encrypt vault with honey accounts
ciphertext, metadata = vault_system.encrypt_vault(
    passwords,
    master_password,
    honey_accounts=[
        HoneyAccount(
            website=acc['website'],
            username=acc['username'],
            password=acc['password'],
            created_at=datetime.now()
        ) for acc in honey_accounts
    ]
)

# Setup monitoring
config = MonitorConfig(
    check_interval_seconds=300,
    email_alerts_enabled=True,
    smtp_username="your-email@gmail.com",
    smtp_password="your-app-password",
    alert_recipients=["user@example.com"]
)

monitor = HoneyAccountMonitor(config)

# Start monitoring (detects breaches automatically)
async def on_breach(alert):
    print(f"🚨 BREACH DETECTED: {alert.website}")
    # Take action: change passwords, lock vault, etc.

await monitor.start_monitoring(honey_accounts, on_breach)
```

### 3. Command-Line Interface

```bash
# Create new vault
python cli.py create --master-password "YourPassword123!"

# Add password
python cli.py add --website github.com --username user --password GitHubPass

# List passwords
python cli.py list

# Export vault
python cli.py export --output vault_backup.json

# Start honey account monitoring
python cli.py monitor --config monitor_config.json
```

---

## 🔐 Security Features

### 1. Honey Encryption

**How it works**:
- Encrypts passwords into a seed using probability distribution
- Incorrect master passwords produce random seeds
- Random seeds decode to plausible-looking passwords
- Attacker cannot distinguish real from decoy offline

**Security guarantee**: Information-theoretic security against offline attacks

### 2. Transformer-Based Vault Model

- **85 million parameters** trained on real password data
- Captures password patterns and user behavior
- Generates realistic decoy passwords
- Models password reuse and similarity

**Example output**:
```python
# Real vault
["MyGitHub2024!", "EmailPass123", "Facebook@456"]

# Decoy vault (from random seed)
["GitHub_pass99", "mail2024Pass", "SocialNet!23"]
# ↑ Looks real but completely fake!
```

### 3. Measure I: Selective Encryption

Some websites lack proper rate limiting. For these sites:
- Generate **random passwords** (32+ characters)
- Store in **plaintext** within encrypted vault
- Limits online guessing attempts
- Provides early breach detection

**Configuration**:
```python
HoneyVault.UNLIMITED_LOGIN_SITES = {
    'gaming-site.com',
    'forum-example.com',
    # Add sites as discovered
}
```

### 4. Measure II: Honey Accounts

- **10-20 fake accounts** embedded in vault
- Monitor for unauthorized login attempts
- Instant breach alerts via email/webhook
- Zero false negatives (any access = breach)

**Websites supported**:
- GitHub (API monitoring)
- Gmail (email notifications)
- Dropbox, AWS, etc.

### 5. Defense-in-Depth Architecture

```
Layer 1: Strong Master Password (PBKDF2, 100k iterations)
Layer 2: AES-256-GCM Encryption
Layer 3: Honey Encryption (plausible decoys)
Layer 4: Selective Encryption (limit attempts)
Layer 5: Honey Accounts (breach detection)
Layer 6: Rate Limiting (online verification)
```

---

## 🎓 Training Your Own Model

### Prepare Dataset

```python
from training_pipeline import load_vault_data, VaultDataset, VaultTrainer, TrainingConfig

# Load your vault dataset
# Format: JSON with {"vaults": [[pwd1, pwd2, ...], [pwd3, pwd4, ...], ...]}
vaults = load_vault_data("path/to/vault_dataset.json")

# Split into train/val
split_idx = int(len(vaults) * 0.9)
train_vaults = vaults[:split_idx]
val_vaults = vaults[split_idx:]
```

### Train Model

```python
# Configuration
config = TrainingConfig(
    batch_size=32,
    num_epochs=5,
    learning_rate=1e-4,
    warmup_steps=1000,
    device="cuda"  # or "cpu"
)

# Initialize
tokenizer = VaultTokenizer()
model = VaultTransformer(vocab_size=tokenizer.vocab_size)

train_dataset = VaultDataset(train_vaults, tokenizer)
val_dataset = VaultDataset(val_vaults, tokenizer)

# Train
trainer = VaultTrainer(model, config, train_dataset, val_dataset)
trainer.train()

# Export for production
from training_pipeline import export_to_onnx
export_to_onnx(model, "vault_model.onnx")
```

### Training Tips

1. **Dataset Size**: Minimum 100k vaults, ideally 1M+ vaults
2. **Data Quality**: Clean, deduplicate, remove malformed passwords
3. **Compute**: GPU recommended (training takes ~8 hours on RTX 3090)
4. **Hyperparameters**: Adjust based on dataset size and quality

---

## 📚 API Reference

### Core Classes

#### `HoneyVault`

Main vault system interface.

```python
class HoneyVault:
    def __init__(
        self,
        model: Optional[VaultTransformer] = None,
        tokenizer: Optional[VaultTokenizer] = None,
        kdf_iterations: int = 100000
    )
    
    def encrypt_vault(
        self,
        passwords: List[Dict[str, str]],
        master_password: str,
        honey_accounts: Optional[List[HoneyAccount]] = None
    ) -> Tuple[bytes, VaultMetadata]
    
    def decrypt_vault(
        self,
        ciphertext: bytes,
        master_password: str,
        metadata: VaultMetadata
    ) -> List[Dict[str, str]]
    
    def add_password(
        self,
        old_ciphertext: bytes,
        old_metadata: VaultMetadata,
        master_password: str,
        new_entry: Dict[str, str]
    ) -> Tuple[bytes, VaultMetadata]
```

#### `VaultTransformer`

Transformer model for password distribution.

```python
class VaultTransformer(nn.Module):
    def __init__(
        self,
        vocab_size: int = 98,
        d_model: int = 768,
        nhead: int = 12,
        num_layers: int = 12
    )
    
    def generate_password(
        self,
        context: str,
        tokenizer: VaultTokenizer,
        max_length: int = 25,
        temperature: float = 1.0
    ) -> str
    
    def calculate_vault_probability(
        self,
        vault: List[str],
        tokenizer: VaultTokenizer
    ) -> float
```

#### `HoneyAccountMonitor`

Monitors honey accounts for breaches.

```python
class HoneyAccountMonitor:
    def __init__(self, config: MonitorConfig)
    
    async def start_monitoring(
        self,
        honey_accounts: List[Dict],
        alert_callback: Optional[Callable] = None
    )
    
    async def stop_monitoring(self)
```

---

## ⚙️ Advanced Configuration

### Environment Variables

```bash
# .env file
GUARDLOCKER_DATA_DIR=/var/guardlocker/data
GUARDLOCKER_MODEL_PATH=/var/guardlocker/models/vault_model.onnx
GUARDLOCKER_KDF_ITERATIONS=100000
GUARDLOCKER_LOG_LEVEL=INFO

# Monitoring
SMTP_SERVER=smtp.gmail.com
SMTP_PORT=587
SMTP_USERNAME=your-email@gmail.com
SMTP_PASSWORD=your-app-password
ALERT_RECIPIENTS=user1@example.com,user2@example.com

# Security
MAX_LOGIN_ATTEMPTS=5
RATE_LIMIT_WINDOW=3600  # 1 hour
SESSION_TIMEOUT=1800  # 30 minutes
```

### Custom Model Configuration

```python
# Custom Transformer size
model = VaultTransformer(
    vocab_size=98,
    d_model=512,  # Smaller model
    nhead=8,
    num_layers=6,
    dim_feedforward=2048
)
# ~22M parameters instead of 85M
```

### Production Deployment

```yaml
# docker-compose.yml
version: '3.8'
services:
  guardlocker:
    image: guardlocker:latest
    ports:
      - "8000:8000"
    environment:
      - DATABASE_URL=postgresql://user:pass@db:5432/guardlocker
      - REDIS_URL=redis://redis:6379
    volumes:
      - ./data:/data
      - ./models:/models
    depends_on:
      - db
      - redis
  
  db:
    image: postgres:15
    environment:
      - POSTGRES_DB=guardlocker
      - POSTGRES_USER=user
      - POSTGRES_PASSWORD=password
    volumes:
      - postgres_data:/var/lib/postgresql/data
  
  redis:
    image: redis:7-alpine
    volumes:
      - redis_data:/data

volumes:
  postgres_data:
  redis_data:
```

---

## 📊 Performance

### Encryption/Decryption Speed

| Vault Size | Encode Time | Decode Time | Hardware |
|------------|-------------|-------------|----------|
| 10 passwords | 0.64s | 0.47s | NVIDIA 3090 |
| 20 passwords | 1.23s | 0.94s | NVIDIA 3090 |
| 50 passwords | 3.08s | 2.35s | NVIDIA 3090 |
| 10 passwords | 2.24s | 1.65s | Kirin 888 |
| 20 passwords | 4.31s | 3.29s | Kirin 888 |

### Model Size

| Model | Parameters | Size (32-bit) | Size (16-bit) | Size (INT8) |
|-------|------------|---------------|---------------|-------------|
| Full | 85M | 326 MB | 163 MB | 82 MB |
| Compact | 22M | 85 MB | 43 MB | 22 MB |

### Security Performance

Against **1,000 online guessing attempts**:

| Scheme | Avg. Cracked Accounts | With Measures I & II |
|--------|----------------------|----------------------|
| Golla et al. [2016] | 0.76 | 0.34 |
| Cheng et al. [2021] | 0.65 | 0.25 |
| **GuardLocker** | **0.51** | **0.11** |

---

## 🛡️ Security Considerations

### Threat Model

**Protected Against**:
✅ Offline guessing attacks (information-theoretic security)
✅ Dictionary attacks on master password
✅ Ciphertext-only attacks
✅ Intersection attacks (with incremental updates)

**Not Protected Against** (require additional measures):
❌ Keyloggers (use secure input methods)
❌ Phishing (user education)
❌ Malware on device (OS-level security)
❌ Rubber-hose cryptanalysis (don't get caught!)

### Best Practices

1. **Master Password**:
   - Minimum 16 characters
   - Mix of letters, numbers, symbols
   - NOT similar to any vault password
   - Use password strength meter

2. **Honey Accounts**:
   - Use 10-20 accounts minimum
   - Select websites with login notifications
   - Use random usernames to prevent DoS
   - Monitor regularly

3. **Backup Strategy**:
   - Export vault regularly
   - Store encrypted backups offline
   - Test recovery procedure
   - Keep multiple backups

4. **Operational Security**:
   - Enable 2FA where possible
   - Monitor honey accounts actively
   - Update weak passwords regularly
   - Review breach alerts promptly

---

## 🤝 Contributing

We welcome contributions! Please see [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.

### Development Setup

```bash
# Install development dependencies
pip install -r requirements-dev.txt

# Run tests
pytest tests/ -v --cov=guardlocker

# Format code
black guardlocker/
isort guardlocker/

# Type checking
mypy guardlocker/

# Lint
flake8 guardlocker/
```

---

## 📖 Research Background

This project implements the honey vault scheme from:

**"Practically Secure Honey Password Vaults: New Design and New Evaluation against Online Guessing"**
- Haibo Cheng et al.
- USENIX Security 2025
- [Paper Link](https://www.usenix.org/conference/usenixsecurity25/presentation/cheng-haibo)

### Key Innovations

1. **Large-Scale Dataset**: 63M vaults (vs. 276 in prior work)
2. **Transformer Model**: 85M parameters for realistic decoys
3. **Practical Security**: Online guessing evaluation
4. **Defense Measures**: Selective encryption + honey accounts
5. **Real-World Usable**: 0.11 accounts cracked per 1000 attempts

### Related Work

- Juels & Ristenpart, "Honey Encryption" (EUROCRYPT 2014)
- Chatterjee et al., "Cracking-Resistant Password Vaults" (IEEE S&P 2015)
- Golla et al., "Security of Password Vaults" (ACM CCS 2016)
- Cheng et al., "Incrementally Updateable Honey Vaults" (USENIX Security 2021)

---

## 📄 License

MIT License - see [LICENSE](LICENSE) file for details.

---

## 🙏 Acknowledgments

- Research team at Peking University
- USENIX Security community
- Open-source contributors

---

## 📞 Support

- **Issues**: [GitHub Issues] https://github.com/lakshyaberia1/-GuardLocker
- **Discussions**: [GitHub Discussions] https://github.com/lakshyaberia1/-GuardLocker/pulls
- **Email**: 
- **Documentation**: 

---

**⚠️ Security Notice**: This is research software. While based on peer-reviewed academic work, it should be thoroughly audited before production use. Always maintain secure backups of your passwords.

**🔒 Remember**: No password manager is perfect. Use strong, unique master passwords, enable all security measures, and monitor honey accounts regularly.

---

Made with ❤️ and 🔐 by the GuardLocker team
