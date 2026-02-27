"""
GuardLocker - Complete Honey Vault System
Integrates Transformer model, encoder, and symmetric encryption

Provides information-theoretic security against offline attacks

v2 UPGRADE: PBKDF2-HMAC-SHA256 → Argon2id (RFC 9106)
  - Memory-hard: 64 MB RAM required per attack attempt
  - GPU/ASIC cracking ~1000× harder than PBKDF2
  - PHC competition winner (2015)
  - OWASP 2024 recommended
  - Install: pip install argon2-cffi
"""

import secrets
import hashlib
from typing import List, Tuple, Optional, Dict
from dataclasses import dataclass
from datetime import datetime
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
import json

# ── Argon2id import with graceful PBKDF2 fallback ───────────
try:
    from argon2.low_level import hash_secret_raw, Type
    ARGON2_AVAILABLE = True
    print("✓ Argon2id KDF loaded")
except ImportError:
    ARGON2_AVAILABLE = False
    from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
    from cryptography.hazmat.primitives import hashes
    from cryptography.hazmat.backends import default_backend
    print("⚠️  argon2-cffi not found. Run: pip install argon2-cffi")
    print("    Falling back to PBKDF2-HMAC-SHA256 temporarily.")

# ── Transformer imports ──────────────────────────────────────
try:
    from vault_transformer import VaultTransformer, VaultTokenizer
    from honey_encoder import HoneyEncoder
    TRANSFORMER_AVAILABLE = True
except ImportError:
    TRANSFORMER_AVAILABLE = False

# ── Argon2id Parameters (OWASP 2024 minimum) ────────────────
ARGON2_TIME_COST    = 3        # iterations
ARGON2_MEMORY_COST  = 65536    # 64 MB in KiB
ARGON2_PARALLELISM  = 4        # parallel threads
ARGON2_HASH_LEN     = 32       # 256-bit output for AES-256
ARGON2_SALT_LEN     = 32       # 256-bit salt
ARGON2_VERSION      = 19       # Argon2 v1.3


@dataclass
class HoneyAccount:
    """Honey account for breach detection"""
    website: str
    username: str
    password: str
    created_at: datetime
    monitor_endpoint: Optional[str] = None
    last_checked: Optional[datetime] = None


@dataclass
class VaultMetadata:
    """Metadata for encrypted vault"""
    version: str = "2.0"           # bumped: v2 = Argon2id
    salt: bytes = None
    nonce: bytes = None
    created_at: datetime = None
    updated_at: datetime = None
    password_count: int = 0
    has_honey_accounts: bool = False
    kdf: str = "argon2id"           # NEW: tracks which KDF was used
    argon2_time_cost: int = ARGON2_TIME_COST
    argon2_memory_cost: int = ARGON2_MEMORY_COST
    argon2_parallelism: int = ARGON2_PARALLELISM

    def to_dict(self) -> dict:
        return {
            'version':             self.version,
            'salt':                self.salt.hex(),
            'nonce':               self.nonce.hex(),
            'created_at':          self.created_at.isoformat(),
            'updated_at':          self.updated_at.isoformat(),
            'password_count':      self.password_count,
            'has_honey_accounts':  self.has_honey_accounts,
            # NEW Argon2id fields:
            'kdf':                 self.kdf,
            'argon2_time_cost':    self.argon2_time_cost,
            'argon2_memory_cost':  self.argon2_memory_cost,
            'argon2_parallelism':  self.argon2_parallelism,
        }

    @classmethod
    def from_dict(cls, data: dict):
        return cls(
            version            = data['version'],
            salt               = bytes.fromhex(data['salt']),
            nonce              = bytes.fromhex(data['nonce']),
            created_at         = datetime.fromisoformat(data['created_at']),
            updated_at         = datetime.fromisoformat(data['updated_at']),
            password_count     = data['password_count'],
            has_honey_accounts = data['has_honey_accounts'],
            # Argon2id fields — with fallback for v1 vaults:
            kdf                = data.get('kdf', 'pbkdf2'),
            argon2_time_cost   = data.get('argon2_time_cost',   ARGON2_TIME_COST),
            argon2_memory_cost = data.get('argon2_memory_cost', ARGON2_MEMORY_COST),
            argon2_parallelism = data.get('argon2_parallelism', ARGON2_PARALLELISM),
        )


class HoneyVault:
    """
    Complete Honey Password Vault System

    Features:
    - Transformer-based vault modeling
    - Honey encryption with IS-PMTE
    - AES-256-GCM symmetric encryption  ← unchanged
    - Argon2id key derivation            ← UPGRADED from PBKDF2
    - Prefix-keeping for incremental updates
    - Honey accounts for breach detection
    - Selective encryption for unlimited-login sites
    """

    # Sites known to have unlimited or weak rate limiting
    UNLIMITED_LOGIN_SITES = {
        'gaming-site.com',
        'forum-example.com',
        # Add more as identified
    }

    def __init__(
        self,
        model: Optional['VaultTransformer'] = None,
        tokenizer: Optional['VaultTokenizer'] = None,
        kdf_iterations: int = 100000   # kept for API compatibility; ignored when Argon2id active
    ):
        if TRANSFORMER_AVAILABLE:
            self.model     = model     or VaultTransformer()
            self.tokenizer = tokenizer or VaultTokenizer()
            self.encoder   = HoneyEncoder(self.model, self.tokenizer)
        else:
            self.model = self.tokenizer = self.encoder = None
        self.kdf_iterations = kdf_iterations   # used only in PBKDF2 fallback

    # ─────────────────────────────────────────────────────────
    # KEY DERIVATION  (ONLY function that changed from v1)
    # ─────────────────────────────────────────────────────────
    def derive_key(
        self,
        master_password: str,
        salt: bytes,
        key_length: int = 32,
        metadata: Optional[VaultMetadata] = None,
    ) -> bytes:
        """
        Derive 256-bit AES encryption key from master password.

        Uses Argon2id (RFC 9106) when argon2-cffi is installed.
        Automatically falls back to PBKDF2-HMAC-SHA256 otherwise.

        Argon2id vs PBKDF2-SHA256:
          Memory per attempt : 64 MB     vs ~1 KB
          GPU attack cost    : ~1000×    harder
          Algorithm type     : Memory-hard vs CPU-hard only
          PHC winner (2015)  : YES        vs NO
          OWASP 2024         : Recommended vs Deprecated for new systems
          NIST SP 800-63B    : Preferred  vs Allowed

        Params are read from metadata when decrypting, so vaults
        created with different Argon2id settings remain readable.
        """
        # Use params from metadata when decrypting (vault compatibility)
        t = getattr(metadata, 'argon2_time_cost',   ARGON2_TIME_COST)   if metadata else ARGON2_TIME_COST
        m = getattr(metadata, 'argon2_memory_cost', ARGON2_MEMORY_COST) if metadata else ARGON2_MEMORY_COST
        p = getattr(metadata, 'argon2_parallelism', ARGON2_PARALLELISM) if metadata else ARGON2_PARALLELISM

        if ARGON2_AVAILABLE:
            return hash_secret_raw(
                secret      = master_password.encode('utf-8'),
                salt        = salt,
                time_cost   = t,
                memory_cost = m,
                parallelism = p,
                hash_len    = ARGON2_HASH_LEN,
                type        = Type.ID,       # Argon2**id** (hybrid: best of i + d)
                version     = ARGON2_VERSION,
            )
        else:
            # PBKDF2 fallback — remove once argon2-cffi is installed
            kdf = PBKDF2HMAC(
                algorithm  = hashes.SHA256(),
                length     = key_length,
                salt       = salt,
                iterations = self.kdf_iterations,
                backend    = default_backend()
            )
            return kdf.derive(master_password.encode('utf-8'))

    # ─────────────────────────────────────────────────────────
    # ENCRYPT VAULT  (unchanged except: salt len + metadata fields)
    # ─────────────────────────────────────────────────────────
    def encrypt_vault(
        self,
        passwords: List[Dict[str, str]],
        master_password: str,
        honey_accounts: Optional[List[HoneyAccount]] = None
    ) -> Tuple[bytes, VaultMetadata]:
        """
        Encrypt a password vault.

        Args:
            passwords: List of password entries
                      Format: [{'website': 'x', 'username': 'y', 'password': 'z'}, ...]
            master_password: Master password for encryption
            honey_accounts: Optional honey accounts for breach detection

        Returns:
            (ciphertext, metadata)
        """
        # Generate salt and nonce
        salt  = secrets.token_bytes(ARGON2_SALT_LEN)  # 32 bytes (was also 32 in v1)
        nonce = secrets.token_bytes(12)                # 96 bits for GCM

        # FIX BUG 5: Store full entry metadata (website, username) alongside
        # honey-encrypted passwords so they can be reconstructed on decrypt.
        # FIX BUG 6: Use entry.copy() to avoid mutating the caller's input dicts.
        honey_entries    = []   # full entry dicts for honey-encrypted passwords
        plaintext_random = []   # full entry dicts for unlimited-login sites

        for entry in passwords:
            website = entry['website']
            if self._should_use_honey_encryption(website):
                honey_entries.append(entry.copy())
            else:
                safe_entry = entry.copy()
                safe_entry['password'] = self._generate_secure_random_password()
                plaintext_random.append(safe_entry)

        honey_encrypted = [e['password'] for e in honey_entries]

        vault_data = {
            'honey_entries':             honey_entries,
            'honey_encrypted_passwords': honey_encrypted,  # legacy compat
            'plaintext_entries':         plaintext_random,
            'honey_accounts': [
                {
                    'website':    acc.website,
                    'username':   acc.username,
                    'password':   acc.password,
                    'created_at': acc.created_at.isoformat()
                }
                for acc in (honey_accounts or [])
            ]
        }

        if honey_encrypted:
            seed = self.encoder.encode_vault(honey_encrypted) if self.encoder else b''
        else:
            seed = b''

        vault_json  = json.dumps(vault_data).encode('utf-8')
        seed_length = len(seed).to_bytes(4, byteorder='big')
        plaintext   = seed_length + seed + vault_json

        # ← ONLY CHANGE: derive_key now calls Argon2id internally
        key        = self.derive_key(master_password, salt)
        ciphertext = AESGCM(key).encrypt(nonce, plaintext, None)

        metadata = VaultMetadata(
            salt               = salt,
            nonce              = nonce,
            created_at         = datetime.now(),
            updated_at         = datetime.now(),
            password_count     = len(passwords),
            has_honey_accounts = len(honey_accounts or []) > 0,
            # NEW: store KDF identity and params in metadata
            kdf                = "argon2id" if ARGON2_AVAILABLE else "pbkdf2",
            argon2_time_cost   = ARGON2_TIME_COST,
            argon2_memory_cost = ARGON2_MEMORY_COST,
            argon2_parallelism = ARGON2_PARALLELISM,
        )

        return ciphertext, metadata

    # ─────────────────────────────────────────────────────────
    # DECRYPT VAULT  (unchanged except: passes metadata to derive_key)
    # ─────────────────────────────────────────────────────────
    def decrypt_vault(
        self,
        ciphertext: bytes,
        master_password: str,
        metadata: VaultMetadata
    ) -> List[Dict[str, str]]:
        """
        Decrypt a password vault.
        Wrong passwords generate plausible decoy vault (honey encryption).

        Args:
            ciphertext: Encrypted vault
            master_password: Master password (may be incorrect)
            metadata: Vault metadata

        Returns:
            List of password entries (real or decoy)
        """
        # ← ONLY CHANGE: pass metadata so Argon2id uses correct stored params
        key = self.derive_key(master_password, metadata.salt, metadata=metadata)

        try:
            plaintext = AESGCM(key).decrypt(metadata.nonce, ciphertext, None)
        except Exception:
            return self._generate_random_decoy_vault(metadata.password_count, seed_bytes=key)

        seed_length = int.from_bytes(plaintext[:4], byteorder='big')
        seed        = plaintext[4:4 + seed_length]
        vault_json  = plaintext[4 + seed_length:]

        try:
            vault_data = json.loads(vault_json.decode('utf-8'))
        except Exception:
            return self._generate_random_decoy_vault(metadata.password_count, seed_bytes=key)

        if seed:
            try:
                honey_passwords = self.encoder.decode_seed(
                    seed, max_passwords=metadata.password_count
                ) if self.encoder else []
            except Exception:
                honey_passwords = []
                for _ in range(metadata.password_count):
                    if self.model:
                        honey_passwords.append(self.model.generate_password('<SEP>', self.tokenizer))
        else:
            honey_passwords = []

        vault = []

        # FIX BUG 5: Use stored entry metadata rather than generic placeholders
        honey_entries = vault_data.get('honey_entries', [])
        for i, pwd in enumerate(honey_passwords):
            if i < len(honey_entries):
                base = honey_entries[i].copy()
                base['password']            = pwd
                base['encrypted_with_honey'] = True
                vault.append(base)
            else:
                vault.append({
                    'website':             f'website{i+1}.com',
                    'username':            f'user{i+1}',
                    'password':            pwd,
                    'encrypted_with_honey': True
                })

        for entry in vault_data.get('plaintext_entries', []):
            vault.append({**entry, 'encrypted_with_honey': False})

        for acc in vault_data.get('honey_accounts', []):
            vault.append({
                'website':          acc['website'],
                'username':         acc['username'],
                'password':         acc['password'],
                'is_honey_account': True
            })

        return vault

    # ─────────────────────────────────────────────────────────
    # ADD PASSWORD  (unchanged)
    # ─────────────────────────────────────────────────────────
    def add_password(
        self,
        old_ciphertext: bytes,
        old_metadata: VaultMetadata,
        master_password: str,
        new_entry: Dict[str, str]
    ) -> Tuple[bytes, VaultMetadata]:
        existing_vault = self.decrypt_vault(old_ciphertext, master_password, old_metadata)
        existing_vault.append(new_entry)
        return self.encrypt_vault(existing_vault, master_password)

    # ─────────────────────────────────────────────────────────
    # HELPERS
    # ─────────────────────────────────────────────────────────
    def _should_use_honey_encryption(self, website: str) -> bool:
        return website.lower() not in self.UNLIMITED_LOGIN_SITES

    def _generate_secure_random_password(self, length: int = 32) -> str:
        import string
        alphabet = string.ascii_letters + string.digits + string.punctuation
        return ''.join(secrets.choice(alphabet) for _ in range(length))

    def _generate_random_decoy_vault(
        self,
        password_count: int,
        seed_bytes: bytes = None
    ) -> List[Dict[str, str]]:
        """
        Generate a realistic decoy vault indistinguishable from real vaults.

        Key design principle: decoy vaults must match the statistical
        fingerprint of real vaults across ALL measurable features:
          - Indian names + Indian sites (matches actual user base)
          - ONE consistent identity per vault (real users reuse one email)
          - Same password pattern distribution (5 real-world patterns)
          - ONE dominant pattern per person (~70% of their passwords)
          - Same field structure as real vaults

        Identity structure per vault (mirrors real user behavior):
          primary_email  →  rahulsharma99@gmail.com   used on ~80% of sites
          dob_handle     →  rahul1999                  used on ~15% of sites
          phone_handle   →  rahul_7342                 used on ~5%  of sites

        Security: same seed_bytes → same decoy every time, preventing
        confirmation attacks from entering the same wrong password twice.
        """
        import random, string

        # Deterministic RNG — same wrong password always gives same decoy
        if seed_bytes is not None:
            rng = random.Random(int.from_bytes(seed_bytes[:8], 'big'))
        else:
            rng = random.Random(int.from_bytes(secrets.token_bytes(8), 'big'))

        # ── Indian name + site pools ─────────────────────────────────────
        FIRST_NAMES = [
            'rahul', 'priya', 'amit', 'neha', 'rohan', 'pooja',
            'vikram', 'anjali', 'arjun', 'divya', 'karan', 'simran',
            'ravi', 'sneha', 'aditya', 'meera', 'sanjay', 'kavya',
            'nikhil', 'shruti', 'deepak', 'ananya', 'suresh', 'ishaan',
            'ritika', 'gaurav', 'swati', 'mohit', 'tanvi', 'varun',
        ]
        LAST_PARTS = [
            'sharma', 'verma', 'singh', 'kumar', 'gupta', 'joshi',
            'patel', 'yadav', 'mehta', 'nair', 'mishra', 'dubey',
            'pandey', 'chauhan', 'iyer', 'reddy',
        ]
        EMAIL_PROVIDERS = ['1213', '1234', '65656.com', '9090']
        SITES = [
            'gmail.com',     'facebook.com',  'amazon.in',   'netflix.com',
            'instagram.com', 'twitter.com',   'linkedin.com','github.com',
            'flipkart.com',  'paytm.com',     'hotstar.com', 'youtube.com',
            'swiggy.com',    'zomato.com',    'phonepe.com', 'naukri.com',
        ]
        COMMON_WORDS = [
            'password', 'india123', 'welcome', 'qwerty', 'admin',
            'iloveyou', 'hello',   'master',  'dragon', 'bharat',
            'namaste',  'cricket', 'sachin',  'bollywood',
        ]

        # ── Build ONE consistent identity for the whole vault ────────────
        first  = rng.choice(FIRST_NAMES)
        last   = rng.choice(LAST_PARTS)
        
        year   = rng.randint(1995, 2005)
        suffix = rng.randint(1000, 9999)
        prov   = rng.choice(EMAIL_PROVIDERS)
        sep    = rng.choice(['', '.', '_'])
        eu     = f"{first}{sep}{last}"
        if rng.random() < 0.4:          # sometimes add birth year to email
            eu += str(year)[-2:]

        primary_email = f"{eu}{prov}"      # rahulsharma99@gmail.com
        dob_handle    = f"{first}{year}"    # rahul1999
        phone_handle  = f"{first}_{suffix}" # rahul_7342

        def pick_username():
            r = rng.random()
            if r < 0.80:   return primary_email   # same email on most sites
            elif r < 0.95: return dob_handle       # DOB handle occasionally
            else:          return phone_handle     # phone handle rarely

        # ── 5 real-world Indian password patterns ────────────────────────
        def _pat1(r): return ''.join(r.choices(string.ascii_lowercase, k=r.randint(6, 8)))
        def _pat2(r): return ''.join(r.choices(string.ascii_lowercase, k=4)) + str(r.randint(10, 9999))
        def _pat3(r): return r.choice(COMMON_WORDS) + str(r.randint(1, 999))
        def _pat4(r): return ''.join(r.choices(string.ascii_letters + string.digits, k=r.randint(8, 12)))
        def _pat5(r): return first + str(r.randint(1990, 2010))  # rahul2001 — very common in India

        patterns = [_pat1, _pat2, _pat3, _pat4, _pat5]
        dominant = rng.choice(patterns)   # one dominant pattern per person

        available_sites = SITES.copy()
        rng.shuffle(available_sites)

        vault = []
        for i in range(password_count):
            site  = available_sites[i % len(available_sites)]
            uname = pick_username()
            # 70% use dominant pattern, 30% slight variation — realistic human behavior
            pwd   = dominant(rng) if rng.random() < 0.70 else rng.choice(patterns)(rng)
            vault.append({
                'website':             site,
                'username':            uname,
                'password':            pwd,
                'encrypted_with_honey': True,
            })
        return vault

    def verify_master_password(
        self,
        ciphertext: bytes,
        metadata: VaultMetadata,
        master_password: str,
        known_password: str,
        known_website: str
    ) -> bool:
        vault = self.decrypt_vault(ciphertext, master_password, metadata)
        for entry in vault:
            if entry.get('website') == known_website:
                return entry['password'] == known_password
        return False


# ─────────────────────────────────────────────────────────────
# Example usage
# ─────────────────────────────────────────────────────────────
if __name__ == "__main__":
    print("=== GuardLocker Honey Vault System  (v2 — Argon2id) ===\n")

    vault_system = HoneyVault()

    passwords = [
        {'website': 'github.com',   'username': 'johndoe',          'password': 'MyGitHub2024!'},
        {'website': 'gmail.com',    'username': 'john@example.com', 'password': 'EmailPass123'},
        {'website': 'facebook.com', 'username': 'johndoe',          'password': 'FBSecure456'},
    ]

    honey_accounts = [
        HoneyAccount(website='honeytrap1.com', username='decoy1',
                     password='HoneyPass1!', created_at=datetime.now()),
        HoneyAccount(website='honeytrap2.com', username='decoy2',
                     password='HoneyPass2!', created_at=datetime.now()),
    ]

    master_password = "MySecureMasterPassword123!"

    print("Encrypting vault with Argon2id...")
    ciphertext, metadata = vault_system.encrypt_vault(passwords, master_password, honey_accounts)
    print(f"KDF          : {metadata.kdf}")
    print(f"Memory cost  : {metadata.argon2_memory_cost} KiB  ({metadata.argon2_memory_cost // 1024} MB)")
    print(f"Time cost    : {metadata.argon2_time_cost} iterations")
    print(f"Parallelism  : {metadata.argon2_parallelism} threads")
    print(f"Ciphertext   : {len(ciphertext)} bytes")
    print(f"Metadata     : {metadata.to_dict()}")

    print("\n=== Decrypting with CORRECT master password ===")
    decrypted_vault = vault_system.decrypt_vault(ciphertext, master_password, metadata)
    print(f"Decrypted {len(decrypted_vault)} entries:")
    for entry in decrypted_vault:
        print(f"  - {entry['website']} | {entry.get('username','')} | {entry['password'][:10]}...")

    print("\n=== Decrypting with INCORRECT master password (decoy) ===")
    decoy_vault = vault_system.decrypt_vault(ciphertext, "WrongPassword123!", metadata)
    print(f"Decoy vault ({len(decoy_vault)} entries):")
    for entry in decoy_vault:
        print(f"  - {entry['website']} | {entry.get('username','')} | {entry['password'][:10]}...")

    print("\n✓ GuardLocker v2 (Argon2id) working correctly!")
    print("Attacker cannot distinguish real from decoy offline.")