#!/usr/bin/env python3
"""
DIAGNOSTIC SCRIPT - Run this to find the problem
"""
import os
import sys

print("="*70)
print("🔍 GUARDLOCKER PATH DIAGNOSTIC")
print("="*70)

# Where is THIS script?
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
print(f"\n1️⃣  THIS SCRIPT IS LOCATED AT:")
print(f"   {SCRIPT_DIR}")

# What's the parent directory?
PROJECT_ROOT = os.path.dirname(SCRIPT_DIR)
print(f"\n2️⃣  PARENT DIRECTORY (assumed project root):")
print(f"   {PROJECT_ROOT}")

# List what's in the parent directory
print(f"\n3️⃣  FOLDERS IN PARENT DIRECTORY:")
try:
    items = os.listdir(PROJECT_ROOT)
    for item in sorted(items):
        item_path = os.path.join(PROJECT_ROOT, item)
        if os.path.isdir(item_path):
            print(f"   📁 {item}")
except Exception as e:
    print(f"   ❌ Error: {e}")

# Check for CORE SYSTEM folder
print(f"\n4️⃣  CHECKING FOR 'CORE SYSTEM' FOLDER:")
core_paths_to_check = [
    os.path.join(PROJECT_ROOT, 'CORE SYSTEM'),
    os.path.join(PROJECT_ROOT, 'CORE_SYSTEM'),
    os.path.join(SCRIPT_DIR, 'CORE SYSTEM'),
    os.path.join(SCRIPT_DIR, 'CORE_SYSTEM'),
]

for path in core_paths_to_check:
    exists = "✅ EXISTS" if os.path.exists(path) else "❌ NOT FOUND"
    print(f"   {exists}: {path}")

# Check for WEB INTERFACE/web_ui
print(f"\n5️⃣  CHECKING FOR 'web_ui' FOLDER:")
web_ui_paths = [
    os.path.join(SCRIPT_DIR, 'web_ui'),
    os.path.join(PROJECT_ROOT, 'WEB INTERFACE', 'web_ui'),
    os.path.join(PROJECT_ROOT, 'WEB_INTERFACE', 'web_ui'),
    os.path.join(PROJECT_ROOT, 'web_ui'),
]

for path in web_ui_paths:
    exists = "✅ EXISTS" if os.path.exists(path) else "❌ NOT FOUND"
    print(f"   {exists}: {path}")
    if os.path.exists(path):
        templates = os.path.join(path, 'templates')
        index = os.path.join(templates, 'index.html')
        print(f"        Templates: {'✅' if os.path.exists(templates) else '❌'}")
        print(f"        index.html: {'✅' if os.path.exists(index) else '❌'}")

# Check for Python modules
print(f"\n6️⃣  CHECKING FOR PYTHON MODULES:")
modules_to_find = [
    'vault_transformer.py',
    'honey_vault_system.py',
    'honey_encoder.py',
    'honey_monitor.py',
]

for module in modules_to_find:
    found_at = None
    # Check in multiple locations
    locations = [
        SCRIPT_DIR,
        PROJECT_ROOT,
        os.path.join(PROJECT_ROOT, 'CORE SYSTEM'),
        os.path.join(PROJECT_ROOT, 'CORE_SYSTEM'),
    ]
    
    for loc in locations:
        module_path = os.path.join(loc, module)
        if os.path.exists(module_path):
            found_at = module_path
            break
    
    if found_at:
        print(f"   ✅ {module}: {found_at}")
    else:
        print(f"   ❌ {module}: NOT FOUND")

print("\n" + "="*70)
print("📋 SUMMARY:")
print("="*70)

# Determine the correct structure
core_found = os.path.exists(os.path.join(PROJECT_ROOT, 'CORE SYSTEM'))
core_alt_found = os.path.exists(os.path.join(PROJECT_ROOT, 'CORE_SYSTEM'))
web_ui_found = None

for path in web_ui_paths:
    if os.path.exists(path):
        web_ui_found = path
        break

if core_found:
    print("✅ Found 'CORE SYSTEM' folder (with space)")
elif core_alt_found:
    print("✅ Found 'CORE_SYSTEM' folder (renamed, no space)")
else:
    print("❌ Cannot find CORE SYSTEM folder!")

if web_ui_found:
    print(f"✅ Found web_ui at: {web_ui_found}")
else:
    print("❌ Cannot find web_ui folder!")

print("\n" + "="*70)
print("💡 RECOMMENDATION:")
print("="*70)

if not core_found and not core_alt_found:
    print("⚠️  CORE SYSTEM folder not found relative to this script!")
    print("   Please verify your folder structure.")
    print(f"   This script is in: {SCRIPT_DIR}")
    print(f"   Looking for CORE SYSTEM in: {PROJECT_ROOT}")

if not web_ui_found:
    print("⚠️  web_ui folder not found!")
    print("   Make sure web_ui/templates/index.html exists")

print("\n")