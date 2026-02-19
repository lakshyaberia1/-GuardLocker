
#!/usr/bin/env python3
"""
GuardLocker Web Server - ENHANCED VERSION
✓ Telegram alerts on wrong password attempts
✓ Bulk data generation (2M+ passwords)
✓ Fixed decoy vault
✓ Better authentication
"""

from flask import Flask, render_template, request, jsonify, send_from_directory, session
from flask_cors import CORS
import os
import sys
import json
from datetime import datetime
import secrets
import hashlib
import requests
import time

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Import GuardLocker modules
try:
    from honey_vault_system import HoneyVault
    from honey_monitor import HoneyAccountGenerator
    from vault_transformer import VaultTransformer, VaultTokenizer
    MODULES_AVAILABLE = True
except ImportError:
    print("Warning: GuardLocker modules not found. Running in demo mode.")
    MODULES_AVAILABLE = False

app = Flask(__name__, 
            template_folder='web_ui/templates',
            static_folder='web_ui/static')
CORS(app)
app.secret_key = secrets.token_hex(32)

# ============ TELEGRAM CONFIGURATION ============
# Set these environment variables or edit here:
TELEGRAM_BOT_TOKEN = '8511379034:AAEH4QNCBQWBXjm5uytYf5-jDAXmHvpk3jg'# os.getenv('TELEGRAM_BOT_TOKEN', '')  # remove added telegram bot then get your token from here  @BotFather
TELEGRAM_CHAT_ID = '5590835443' #os.getenv('TELEGRAM_CHAT_ID', '')     # # remove added telegram bot then get Your chat ID

def send_telegram_alert(message: str, is_critical: bool = True):
    """
    Send alert to Telegram
    
    Args:
        message: Alert message
        is_critical: If True, adds 🚨 emoji
    """
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        print("⚠️ Telegram not configured. Skipping alert.")
        return False
    
    try:
        emoji = "🚨" if is_critical else "ℹ️"
        full_message = f"{emoji} *GuardLocker Alert*\n\n{message}"
        
        url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
        payload = {
            'chat_id': TELEGRAM_CHAT_ID,
            'text': full_message,
            'parse_mode': 'Markdown'
        }
        
        response = requests.post(url, json=payload, timeout=5)
        
        if response.status_code == 200:
            print("✓ Telegram alert sent")
            return True
        else:
            print(f"✗ Telegram alert failed: {response.status_code}")
            return False
            
    except Exception as e:
        print(f"✗ Telegram error: {e}")
        return False

# ============ VAULT DATA STORAGE ============
vault_system = None

vault_data = {
    'master_password_hash': None,
    'ciphertext': None,
    'metadata': None,
    'real_passwords': [],
    'honey_accounts': [],
    'locked': True,
    'failed_attempts': 0,  # Track wrong password attempts
    'last_attempt_time': None,
    'created_at': None
}

# ============ BULK GENERATION CACHE ============
bulk_generated_passwords = []  # Store 2M+ passwords here

def hash_password(password: str) -> str:
    """SHA256 hash for password verification"""
    return hashlib.sha256(password.encode('utf-8')).hexdigest()

def init_vault_system():
    """Initialize the vault system"""
    global vault_system
    if MODULES_AVAILABLE and vault_system is None:
        try:
            vault_system = HoneyVault()
            print("✓ Vault system initialized")
        except Exception as e:
            print(f"✗ Failed to initialize vault system: {e}")
            print("Running in demo mode")

def generate_demo_decoy_passwords(count: int = 5):
    """Generate fake but realistic-looking passwords for demo decoy mode"""
    import random
    import string
    
    decoy_passwords = []
    demo_sites = [
        'github.com', 'gmail.com', 'dropbox.com', 'linkedin.com', 
        'twitter.com', 'facebook.com', 'netflix.com', 'spotify.com',
        'amazon.com', 'reddit.com'
    ]
    
    usernames = [
        'john_doe', 'sarah_m', 'alex_tech', 'demo_user', 'test_account',
        'user_2024', 'secure_user', 'my_account', 'webuser', 'profile_1'
    ]
    
    for i in range(count):
        patterns = [
            lambda: ''.join(random.choices(string.ascii_letters, k=8)) + ''.join(random.choices(string.digits, k=3)) + '!',
            lambda: 'Password' + str(random.randint(100, 999)) + random.choice(['!', '@', '#']),
            lambda: random.choice(['Secure', 'Safe', 'Private']) + str(random.randint(2020, 2025)),
            lambda: ''.join(random.choices(string.ascii_uppercase, k=1)) + ''.join(random.choices(string.ascii_lowercase, k=6)) + str(random.randint(10, 99)),
        ]
        
        decoy_passwords.append({
            'website': demo_sites[i % len(demo_sites)],
            'username': usernames[i % len(usernames)],
            'password': random.choice(patterns)(),
            'is_decoy': True
        })
    
    return decoy_passwords

# ============ API ROUTES ============

@app.route('/')
def index():
    """Serve the main page"""
    return render_template('index.html')

@app.route('/static/<path:path>')
def send_static(path):
    """Serve static files"""
    return send_from_directory('web_ui/static', path)

@app.route('/api/vault/create', methods=['POST'])
def create_vault():
    """Create a new vault with master password"""
    try:
        data = request.get_json()
        master_password = data.get('master_password')
        
        if not master_password:
            return jsonify({'error': 'Master password required'}), 400
        
        if len(master_password) < 12:
            return jsonify({'error': 'Master password must be at least 12 characters'}), 400
        
        vault_data['master_password_hash'] = hash_password(master_password)
        vault_data['locked'] = True
        vault_data['failed_attempts'] = 0
        vault_data['created_at'] = datetime.now().isoformat()
        
        # Send Telegram notification
        send_telegram_alert(
            f"✅ *New Vault Created*\n"
            f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
            f"Status: Secure vault initialized",
            is_critical=False
        )
        
        if MODULES_AVAILABLE and vault_system:
            passwords = []
            ciphertext, metadata = vault_system.encrypt_vault(passwords, master_password)
            
            vault_data['ciphertext'] = ciphertext
            vault_data['metadata'] = metadata
            vault_data['real_passwords'] = passwords
            vault_data['honey_accounts'] = []
            
            return jsonify({
                'success': True,
                'message': 'Vault created successfully',
                'metadata': {
                    'created_at': datetime.now().isoformat(),
                    'password_count': 0
                }
            })
        else:
            vault_data['real_passwords'] = []
            vault_data['honey_accounts'] = []
            return jsonify({
                'success': True,
                'message': 'Vault created (demo mode)',
                'metadata': {
                    'created_at': datetime.now().isoformat(),
                    'password_count': 0
                }
            })
            
    except Exception as e:
        print(f"Error creating vault: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/vault/unlock', methods=['POST'])
def unlock_vault():
    """
    Unlock vault - SENDS TELEGRAM ALERT ON WRONG PASSWORD
    """
    try:
        data = request.get_json()
        master_password = data.get('master_password')
        
        if not master_password:
            return jsonify({'error': 'Master password required'}), 400
        
        if vault_data['master_password_hash'] is None:
            return jsonify({'error': 'No vault created yet. Please create a vault first.'}), 400
        
        # Verify password
        provided_password_hash = hash_password(master_password)
        is_correct_password = (provided_password_hash == vault_data['master_password_hash'])
        
        # Update last attempt time
        vault_data['last_attempt_time'] = datetime.now().isoformat()
        
        # === CORRECT PASSWORD === 
        if is_correct_password:
            vault_data['locked'] = False
            vault_data['failed_attempts'] = 0  # Reset counter
            
            # Send success notification
            send_telegram_alert(
                f"✅ *Vault Unlocked Successfully*\n"
                f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
                f"Status: Authorized access",
                is_critical=False
            )
            
            if MODULES_AVAILABLE and vault_system and vault_data['ciphertext']:
                try:
                    passwords = vault_system.decrypt_vault(
                        vault_data['ciphertext'],
                        master_password,
                        vault_data['metadata']
                    )
                    
                    vault_data['real_passwords'] = passwords
                    
                    return jsonify({
                        'success': True,
                        'is_real': True,
                        'passwords': passwords,
                        'honey_accounts': vault_data['honey_accounts'],
                        'metadata': {
                            'password_count': len(passwords),
                            'unlocked_at': datetime.now().isoformat(),
                            'vault_type': 'real'
                        }
                    })
                except Exception as e:
                    print(f"Decryption error: {e}")
                    return jsonify({'error': 'Failed to decrypt vault'}), 500
            else:
                return jsonify({
                    'success': True,
                    'is_real': True,
                    'passwords': vault_data['real_passwords'],
                    'honey_accounts': vault_data['honey_accounts'],
                    'metadata': {
                        'password_count': len(vault_data['real_passwords']),
                        'unlocked_at': datetime.now().isoformat(),
                        'vault_type': 'real'
                    }
                })
        
        # === WRONG PASSWORD - SEND TELEGRAM ALERT ===
        else:
            vault_data['failed_attempts'] += 1
            attempt_count = vault_data['failed_attempts']
            
            # Send CRITICAL Telegram alert
            alert_message = (
                f"🚨 *UNAUTHORIZED ACCESS ATTEMPT #{attempt_count}*\n\n"
                f"⏰ Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
                f"🔐 Wrong password entered\n"
                f"📊 Total failed attempts: {attempt_count}\n\n"
                f"⚠️ *Action Required:*\n"
                f"- Check if this was you\n"
                f"- Change master password if suspicious\n"
                f"- Review vault security"
            )
            
            send_telegram_alert(alert_message, is_critical=True)
            
            print(f"⚠️ WRONG PASSWORD ATTEMPT #{attempt_count} - Telegram alert sent")
            print(f"   Generating decoy vault...")
            
            if MODULES_AVAILABLE and vault_system and vault_data['ciphertext']:
                try:
                    decoy_passwords = vault_system.decrypt_vault(
                        vault_data['ciphertext'],
                        master_password,
                        vault_data['metadata']
                    )
                    
                    return jsonify({
                        'success': True,
                        'is_real': False,
                        'passwords': decoy_passwords,
                        'honey_accounts': [],
                        'metadata': {
                            'password_count': len(decoy_passwords),
                            'unlocked_at': datetime.now().isoformat(),
                            'vault_type': 'decoy',
                            'warning': 'This is a decoy vault (wrong password provided)',
                            'failed_attempts': attempt_count
                        }
                    })
                except Exception as e:
                    print(f"Error generating decoy: {e}")
                    decoy_passwords = generate_demo_decoy_passwords(5)
                    
                    return jsonify({
                        'success': True,
                        'is_real': False,
                        'passwords': decoy_passwords,
                        'honey_accounts': [],
                        'metadata': {
                            'password_count': len(decoy_passwords),
                            'unlocked_at': datetime.now().isoformat(),
                            'vault_type': 'decoy',
                            'failed_attempts': attempt_count
                        }
                    })
            else:
                decoy_passwords = generate_demo_decoy_passwords(5)
                
                return jsonify({
                    'success': True,
                    'is_real': False,
                    'passwords': decoy_passwords,
                    'honey_accounts': [],
                    'metadata': {
                        'password_count': len(decoy_passwords),
                        'unlocked_at': datetime.now().isoformat(),
                        'vault_type': 'decoy',
                        'warning': 'Demo mode decoy vault',
                        'failed_attempts': attempt_count
                    }
                })
            
    except Exception as e:
        print(f"Error unlocking vault: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500

@app.route('/api/vault/add-password', methods=['POST'])
def add_password():
    """Add a password to the vault"""
    try:
        data = request.get_json()
        master_password = data.get('master_password')
        website = data.get('website')
        username = data.get('username')
        password = data.get('password')
        
        if not all([master_password, website, username, password]):
            return jsonify({'error': 'All fields required'}), 400
        
        # Verify master password
        provided_password_hash = hash_password(master_password)
        if provided_password_hash != vault_data['master_password_hash']:
            return jsonify({'error': 'Invalid master password'}), 401
        
        new_entry = {
            'website': website,
            'username': username,
            'password': password
        }
        
        if MODULES_AVAILABLE and vault_system:
            passwords = vault_data['real_passwords'] + [new_entry]
            ciphertext, metadata = vault_system.encrypt_vault(passwords, master_password)
            
            vault_data['ciphertext'] = ciphertext
            vault_data['metadata'] = metadata
            vault_data['real_passwords'] = passwords
        else:
            vault_data['real_passwords'].append(new_entry)
        
        return jsonify({
            'success': True,
            'message': 'Password added successfully',
            'password_count': len(vault_data['real_passwords'])
        })
        
    except Exception as e:
        print(f"Error adding password: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/honey/generate', methods=['POST'])
def generate_honey_accounts():
    """Generate honey accounts"""
    try:
        data = request.get_json()
        count = data.get('count', 10)
        
        if MODULES_AVAILABLE and vault_system:
            try:
                generator = HoneyAccountGenerator(vault_system.model)
                honey_accounts = generator.generate_honey_accounts(count=count)
                vault_data['honey_accounts'] = honey_accounts
                
                return jsonify({
                    'success': True,
                    'honey_accounts': honey_accounts,
                    'count': len(honey_accounts),
                    'message': 'Honey accounts generated successfully'
                })
            except Exception as e:
                print(f"Error generating honey accounts with model: {e}")
                honey_accounts = generate_demo_honey_accounts(count)
                vault_data['honey_accounts'] = honey_accounts
                
                return jsonify({
                    'success': True,
                    'honey_accounts': honey_accounts,
                    'count': len(honey_accounts),
                    'message': 'Honey accounts generated (fallback mode)'
                })
        else:
            honey_accounts = generate_demo_honey_accounts(count)
            vault_data['honey_accounts'] = honey_accounts
            
            return jsonify({
                'success': True,
                'honey_accounts': honey_accounts,
                'count': len(honey_accounts),
                'message': 'Honey accounts generated (demo mode)'
            })
        
    except Exception as e:
        print(f"Error in generate_honey_accounts: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': f'Failed to generate honey accounts: {str(e)}'}), 500

def generate_demo_honey_accounts(count: int):
    """Generate demo honey accounts"""
    import random
    demo_sites = [
        'github.com', 'gmail.com', 'dropbox.com', 'aws.amazon.com', 
        'linkedin.com', 'twitter.com', 'facebook.com', 'instagram.com',
        'discord.com', 'slack.com', 'notion.so', 'trello.com'
    ]
    
    honey_accounts = []
    for i in range(min(count, len(demo_sites))):
        honey_accounts.append({
            'website': demo_sites[i],
            'username': f'honey_trap_{i+1}@example.com',
            'password': f'HoneyTrap{random.randint(1000, 9999)}!',
            'created_at': datetime.now().isoformat(),
            'is_honey': True
        })
    
    return honey_accounts

# ============ BULK GENERATION API ============

@app.route('/api/bulk/generate', methods=['POST'])
def bulk_generate_passwords():
    """
    Generate 2M+ passwords for demonstration
    This showcases the system's ability to handle large datasets
    """
    try:
        data = request.get_json()
        count = data.get('count', 100000)  # Default 100k for safety
        batch_size = data.get('batch_size', 10000)  # Generate in batches
        
        # Limit to reasonable maximum
        max_count = 2500000  # 2.5 million max
        if count > max_count:
            count = max_count
        
        print(f"Starting bulk generation of {count:,} passwords...")
        start_time = time.time()
        
        global bulk_generated_passwords
        bulk_generated_passwords = []
        
        # Generate in batches to show progress
        batches = (count + batch_size - 1) // batch_size
        
        for batch_num in range(batches):
            batch_start = batch_num * batch_size
            batch_end = min((batch_num + 1) * batch_size, count)
            batch_count = batch_end - batch_start
            
            # Generate batch
            if MODULES_AVAILABLE and vault_system:
                batch_passwords = [
                    {
                        'id': batch_start + i,
                        'password': vault_system.model.generate_password(
                            '<SEP>',
                            vault_system.tokenizer,
                            temperature=0.9
                        ),
                        'generated_at': datetime.now().isoformat()
                    }
                    for i in range(batch_count)
                ]
            else:
                # Demo mode - generate random passwords
                import random
                import string
                batch_passwords = [
                    {
                        'id': batch_start + i,
                        'password': ''.join(random.choices(
                            string.ascii_letters + string.digits + '!@#$%', 
                            k=random.randint(12, 20)
                        )),
                        'generated_at': datetime.now().isoformat()
                    }
                    for i in range(batch_count)
                ]
            
            bulk_generated_passwords.extend(batch_passwords)
            
            # Log progress
            if (batch_num + 1) % 10 == 0 or batch_num == batches - 1:
                progress = len(bulk_generated_passwords)
                print(f"  Progress: {progress:,}/{count:,} ({progress*100//count}%)")
        
        elapsed_time = time.time() - start_time
        
        print(f"✓ Generated {len(bulk_generated_passwords):,} passwords in {elapsed_time:.2f}s")
        print(f"  Rate: {len(bulk_generated_passwords)/elapsed_time:.0f} passwords/second")
        
        # Send Telegram notification
        send_telegram_alert(
            f"📊 *Bulk Generation Complete*\n\n"
            f"Generated: {len(bulk_generated_passwords):,} passwords\n"
            f"Time: {elapsed_time:.2f} seconds\n"
            f"Rate: {len(bulk_generated_passwords)/elapsed_time:.0f} pwd/sec",
            is_critical=False
        )
        
        return jsonify({
            'success': True,
            'count': len(bulk_generated_passwords),
            'time_seconds': elapsed_time,
            'rate_per_second': len(bulk_generated_passwords) / elapsed_time,
            'sample': bulk_generated_passwords[:10],  # Return sample
            'message': f'Generated {len(bulk_generated_passwords):,} passwords'
        })
        
    except Exception as e:
        print(f"Error in bulk generation: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500

@app.route('/api/bulk/export', methods=['GET'])
def export_bulk_passwords():
    """Export bulk generated passwords to JSON file"""
    try:
        if not bulk_generated_passwords:
            return jsonify({'error': 'No bulk passwords generated yet'}), 400
        
        # Create export file
        export_data = {
            'total_count': len(bulk_generated_passwords),
            'generated_at': datetime.now().isoformat(),
            'passwords': bulk_generated_passwords
        }
        
        filename = f'bulk_passwords_{len(bulk_generated_passwords)}.json'
        filepath = os.path.join('/tmp', filename)
        
        with open(filepath, 'w') as f:
            json.dump(export_data, f, indent=2)
        
        return jsonify({
            'success': True,
            'filename': filename,
            'file_size_mb': os.path.getsize(filepath) / (1024 * 1024),
            'message': f'Exported {len(bulk_generated_passwords):,} passwords'
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/bulk/stats', methods=['GET'])
def get_bulk_stats():
    """Get statistics about bulk generated passwords"""
    try:
        if not bulk_generated_passwords:
            return jsonify({
                'success': True,
                'count': 0,
                'stats': {}
            })
        
        # Calculate stats
        passwords = [p['password'] for p in bulk_generated_passwords]
        
        stats = {
            'total_count': len(passwords),
            'avg_length': sum(len(p) for p in passwords) / len(passwords),
            'min_length': min(len(p) for p in passwords),
            'max_length': max(len(p) for p in passwords),
            'unique_count': len(set(passwords)),
            'duplicate_count': len(passwords) - len(set(passwords))
        }
        
        return jsonify({
            'success': True,
            'count': len(bulk_generated_passwords),
            'stats': stats
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# ============ STATUS ROUTES ============

@app.route('/api/status', methods=['GET'])
def get_status():
    """Get system status"""
    telegram_configured = bool(TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID)
    
    return jsonify({
        'status': 'online',
        'modules_available': MODULES_AVAILABLE,
        'vault_created': vault_data['master_password_hash'] is not None,
        'vault_locked': vault_data['locked'],
        'password_count': len(vault_data['real_passwords']),
        'honey_account_count': len(vault_data['honey_accounts']),
        'failed_attempts': vault_data['failed_attempts'],
        'telegram_alerts': telegram_configured,
        'bulk_passwords_generated': len(bulk_generated_passwords)
    })

@app.route('/api/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    return jsonify({
        'status': 'healthy',
        'timestamp': datetime.now().isoformat()
    })

@app.route('/api/vault/lock', methods=['POST'])
def lock_vault():
    """Lock the vault"""
    vault_data['locked'] = True
    return jsonify({
        'success': True,
        'message': 'Vault locked'
    })

@app.route('/api/telegram/test', methods=['POST'])
def test_telegram():
    """Test Telegram integration"""
    result = send_telegram_alert(
        "🧪 *Test Alert*\n\n"
        "This is a test message from GuardLocker.\n"
        "If you received this, Telegram alerts are working!",
        is_critical=False
        
    )
    
    return jsonify({
        'success': result,
        'message': 'Telegram alert sent' if result else 'Telegram not configured or failed'
    })

if __name__ == '__main__':
    print("=" * 70)
    print("🔒 GuardLocker Web Server - ENHANCED VERSION")
    print("=" * 70)
    print()
    print("NEW FEATURES:")
    print("  🔔 Telegram alerts on wrong password attempts")
    print("  📊 Bulk password generation (2M+ passwords)")
    print("  ✓ Fixed decoy vault generation")
    print("  ✓ Better authentication & error handling")
    print()
    
    # Check Telegram configuration
    if TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID:
        print("Telegram Configuration:")
        print("  ✓ Bot Token: Configured")
        print("  ✓ Chat ID: Configured")
        print("  ✓ Alerts: ENABLED")
        
        # Send startup notification
        send_telegram_alert(
            "🚀 *GuardLocker Started*\n\n"
            f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
            "Status: Server online and monitoring",
            is_critical=False
        )
    else:
        print("Telegram Configuration:")
        print("  ✗ Not configured (optional)")
        print("  ℹ️  Set TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID to enable alerts")
    
    print()
    
    # Initialize vault system
    init_vault_system()
    
    print()
    print("Server Configuration:")
    print(f"  • Modules Available: {'Yes ✓' if MODULES_AVAILABLE else 'No (Demo Mode)'}")
    print(f"  • Host: 0.0.0.0")
    print(f"  • Port: 5000")
    print(f"  • URL: http://localhost:5000")
    print()
    print("API Endpoints:")
    print("  • /api/vault/create - Create new vault")
    print("  • /api/vault/unlock - Unlock vault (sends Telegram alert on wrong password)")
    print("  • /api/honey/generate - Generate honey accounts")
    print("  • /api/bulk/generate - Generate 2M+ passwords")
    print("  • /api/telegram/test - Test Telegram integration")
    print()
    print("Starting server...")
    print("Press Ctrl+C to stop")
    print()
    
    app.run(host='0.0.0.0', port=5000, debug=True)
