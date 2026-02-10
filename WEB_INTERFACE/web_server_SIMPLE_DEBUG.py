#!/usr/bin/env python3
"""
GuardLocker Web Server - SIMPLIFIED VERSION
This version assumes a specific structure and tells you if it's wrong
"""

from flask import Flask, render_template, request, jsonify, send_from_directory
from flask_cors import CORS
import os
import sys
from datetime import datetime

print("\n" + "="*70)
print("🔒 GUARDLOCKER WEB SERVER - STARTING")
print("="*70 + "\n")

# ===========================================================================
# CRITICAL: DEFINE YOUR ACTUAL FOLDER STRUCTURE HERE
# ===========================================================================

# Where is web_server.py located? (automatically detected)
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
print(f"📍 web_server.py is located at:\n   {SCRIPT_DIR}\n")

# ===========================================================================
# OPTION 1: If your structure is:
#   GuardLocker/
#   ├── CORE SYSTEM/         (Python modules here)
#   └── WEB INTERFACE/       (web_server.py is here)
#       └── web_ui/
#           ├── templates/
#           └── static/
# ===========================================================================

# Uncomment these if web_server.py is in "WEB INTERFACE" folder:
PROJECT_ROOT = os.path.dirname(SCRIPT_DIR)  # Go up one level to GuardLocker
CORE_SYSTEM_DIR = os.path.join(PROJECT_ROOT, 'CORE SYSTEM')
WEB_UI_DIR = os.path.join(SCRIPT_DIR, 'web_ui')

# ===========================================================================
# OPTION 2: If your structure is:
#   GuardLocker/
#   ├── CORE SYSTEM/         (Python modules)
#   ├── WEB INTERFACE/
#   │   └── web_ui/
#   │       ├── templates/
#   │       └── static/
#   └── web_server.py        (web_server.py is in root)
# ===========================================================================

# Uncomment these if web_server.py is in GuardLocker root:
# PROJECT_ROOT = SCRIPT_DIR
# CORE_SYSTEM_DIR = os.path.join(PROJECT_ROOT, 'CORE SYSTEM')
# WEB_UI_DIR = os.path.join(PROJECT_ROOT, 'WEB INTERFACE', 'web_ui')

# ===========================================================================
# OPTION 3: Everything in one folder
#   GuardLocker/
#   ├── vault_transformer.py
#   ├── honey_encoder.py
#   ├── ... (all Python files)
#   ├── web_server.py
#   └── web_ui/
#       ├── templates/
#       └── static/
# ===========================================================================

# Uncomment these if everything is in the same folder:
# PROJECT_ROOT = SCRIPT_DIR
# CORE_SYSTEM_DIR = SCRIPT_DIR
# WEB_UI_DIR = os.path.join(SCRIPT_DIR, 'web_ui')

# ===========================================================================
# NOW CHECK IF THE PATHS EXIST
# ===========================================================================

print("🔍 Checking paths:\n")

# Check CORE SYSTEM
if os.path.exists(CORE_SYSTEM_DIR):
    print(f"✅ CORE SYSTEM found at:\n   {CORE_SYSTEM_DIR}")
    sys.path.insert(0, CORE_SYSTEM_DIR)
    
    # List Python files found
    py_files = [f for f in os.listdir(CORE_SYSTEM_DIR) if f.endswith('.py')]
    if py_files:
        print(f"   Found {len(py_files)} Python files:")
        for f in py_files[:5]:  # Show first 5
            print(f"     • {f}")
else:
    print(f"❌ CORE SYSTEM NOT FOUND at:\n   {CORE_SYSTEM_DIR}")
    print(f"   \n   ⚠️  WARNING: Python modules won't load!")

# Check web_ui
print()
if os.path.exists(WEB_UI_DIR):
    print(f"✅ web_ui found at:\n   {WEB_UI_DIR}")
else:
    print(f"❌ web_ui NOT FOUND at:\n   {WEB_UI_DIR}")
    print(f"   \n   ⚠️  CRITICAL: Templates won't load!")

# Check templates
TEMPLATE_DIR = os.path.join(WEB_UI_DIR, 'templates')
if os.path.exists(TEMPLATE_DIR):
    print(f"✅ templates folder found")
else:
    print(f"❌ templates folder NOT FOUND at:\n   {TEMPLATE_DIR}")

# Check index.html
INDEX_HTML = os.path.join(TEMPLATE_DIR, 'index.html')
if os.path.exists(INDEX_HTML):
    print(f"✅ index.html found")
else:
    print(f"❌ index.html NOT FOUND at:\n   {INDEX_HTML}")
    print(f"   \n   ⚠️  THIS IS YOUR PROBLEM! Flask can't find index.html!")

# Check static
STATIC_DIR = os.path.join(WEB_UI_DIR, 'static')
if os.path.exists(STATIC_DIR):
    print(f"✅ static folder found")
else:
    print(f"❌ static folder NOT FOUND")

print("\n" + "="*70)

# If critical paths don't exist, stop here
if not os.path.exists(INDEX_HTML):
    print("\n❌ CANNOT START SERVER - index.html not found!")
    print("\n💡 TO FIX THIS:")
    print("   1. Check the folder structure above")
    print("   2. Edit lines 32-52 of this file to match YOUR structure")
    print("   3. Uncomment the correct OPTION (1, 2, or 3)")
    print(f"   4. Make sure index.html exists at: {INDEX_HTML}\n")
    sys.exit(1)

# ===========================================================================
# IMPORT MODULES
# ===========================================================================

print("\n📦 Loading Python modules...\n")

try:
    from honey_vault_system import HoneyVault
    print("✅ honey_vault_system imported")
except ImportError as e:
    print(f"❌ honey_vault_system: {e}")

try:
    from honey_monitor import HoneyAccountGenerator
    print("✅ honey_monitor imported")
except ImportError as e:
    print(f"❌ honey_monitor: {e}")

try:
    from vault_transformer import VaultTransformer, VaultTokenizer
    print("✅ vault_transformer imported")
except ImportError as e:
    print(f"❌ vault_transformer: {e}")

try:
    from honey_vault_system import HoneyVault
    from honey_monitor import HoneyAccountGenerator
    from vault_transformer import VaultTransformer, VaultTokenizer
    MODULES_AVAILABLE = True
    print("\n✅ All modules loaded successfully!")
except ImportError as e:
    print(f"\n⚠️  Running in DEMO MODE (some modules missing)")
    MODULES_AVAILABLE = False

# ===========================================================================
# CREATE FLASK APP
# ===========================================================================

print(f"\n🌐 Creating Flask app...")
print(f"   Templates: {TEMPLATE_DIR}")
print(f"   Static: {STATIC_DIR}\n")

app = Flask(__name__, 
            template_folder=TEMPLATE_DIR,
            static_folder=STATIC_DIR)
CORS(app)

# Global vault instance
vault_system = None
current_vault_data = {
    'ciphertext': None,
    'metadata': None,
    'passwords': [],
    'honey_accounts': []
}

def init_vault_system():
    """Initialize the vault system"""
    global vault_system
    if MODULES_AVAILABLE and vault_system is None:
        try:
            vault_system = HoneyVault()
            print("✅ Vault system initialized\n")
        except Exception as e:
            print(f"⚠️  Failed to initialize vault: {e}\n")

# ===========================================================================
# ROUTES
# ===========================================================================

@app.route('/')
def index():
    """Serve the main page"""
    print(f"📄 Serving index.html from: {TEMPLATE_DIR}")
    return render_template('index.html')

@app.route('/static/<path:path>')
def send_static(path):
    """Serve static files"""
    return send_from_directory(STATIC_DIR, path)

@app.route('/api/vault/create', methods=['POST'])
def create_vault():
    """Create a new vault"""
    try:
        data = request.get_json()
        master_password = data.get('master_password')
        
        if not master_password:
            return jsonify({'error': 'Master password required'}), 400
        
        if len(master_password) < 12:
            return jsonify({'error': 'Master password must be at least 12 characters'}), 400
        
        # Demo mode always works
        current_vault_data['passwords'] = []
        current_vault_data['honey_accounts'] = []
        return jsonify({
            'success': True,
            'message': 'Vault created (demo mode)',
            'metadata': {
                'created_at': datetime.now().isoformat(),
                'password_count': 0
            }
        })
            
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/vault/unlock', methods=['POST'])
def unlock_vault():
    """Unlock vault"""
    try:
        return jsonify({
            'success': True,
            'passwords': current_vault_data['passwords'],
            'honey_accounts': current_vault_data['honey_accounts'],
            'metadata': {
                'password_count': len(current_vault_data['passwords']),
                'unlocked_at': datetime.now().isoformat()
            }
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/vault/add-password', methods=['POST'])
def add_password():
    """Add password"""
    try:
        data = request.get_json()
        website = data.get('website')
        username = data.get('username')
        password = data.get('password')
        
        if not all([website, username, password]):
            return jsonify({'error': 'All fields required'}), 400
        
        current_vault_data['passwords'].append({
            'website': website,
            'username': username,
            'password': password
        })
        
        return jsonify({
            'success': True,
            'message': 'Password added',
            'password_count': len(current_vault_data['passwords'])
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/status', methods=['GET'])
def get_status():
    """Get status"""
    return jsonify({
        'status': 'online',
        'modules_available': MODULES_AVAILABLE,
        'vault_created': len(current_vault_data['passwords']) > 0,
        'password_count': len(current_vault_data['passwords'])
    })

@app.route('/api/health', methods=['GET'])
def health_check():
    """Health check"""
    return jsonify({'status': 'healthy', 'timestamp': datetime.now().isoformat()})

# ===========================================================================
# START SERVER
# ===========================================================================

if __name__ == '__main__':
    print("="*70)
    print("🚀 STARTING WEB SERVER")
    print("="*70)
    
    init_vault_system()
    
    print(f"   • Mode: {'Production' if MODULES_AVAILABLE else 'Demo'}")
    print(f"   • URL: http://localhost:5000")
    print(f"\n   Press Ctrl+C to stop\n")
    print("="*70 + "\n")
    
    app.run(host='0.0.0.0', port=5000, debug=True)