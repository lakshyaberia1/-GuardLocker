// GuardLocker Application JavaScript

// Global state
let currentVault = {
    isLocked: true,
    masterPassword: null,
    passwords: [],
    honeyAccounts: [],
    metadata: null
};

// API Base URL
const API_URL = 'http://localhost:5000/api';

// Initialize app
document.addEventListener('DOMContentLoaded', function() {
    updateUI();
    checkPasswordStrength();
});

// Toggle password visibility
function togglePassword(inputId) {
    const input = document.getElementById(inputId);
    if (input.type === 'password') {
        input.type = 'text';
    } else {
        input.type = 'password';
    }
}

// Check password strength
function checkPasswordStrength() {
    const input = document.getElementById('masterPassword');
    if (!input) return;
    
    input.addEventListener('input', function() {
        const password = this.value;
        const strengthDiv = document.getElementById('passwordStrength');
        
        if (password.length === 0) {
            strengthDiv.style.display = 'none';
            return;
        }
        
        let strength = 0;
        if (password.length >= 8) strength++;
        if (password.length >= 12) strength++;
        if (/[a-z]/.test(password) && /[A-Z]/.test(password)) strength++;
        if (/\d/.test(password)) strength++;
        if (/[^a-zA-Z0-9]/.test(password)) strength++;
        
        strengthDiv.style.display = 'block';
        if (strength <= 2) {
            strengthDiv.className = 'password-strength weak';
            strengthDiv.textContent = '⚠️ Weak password. Use at least 12 characters with mixed case, numbers, and symbols.';
        } else if (strength <= 4) {
            strengthDiv.className = 'password-strength medium';
            strengthDiv.textContent = '⚡ Medium strength. Consider adding more complexity.';
        } else {
            strengthDiv.className = 'password-strength strong';
            strengthDiv.textContent = '✅ Strong password!';
        }
    });
}

// Create new vault
async function createNewVault() {
    const masterPassword = document.getElementById('masterPassword').value;
    
    if (!masterPassword) {
        showToast('Please enter a master password', 'error');
        return;
    }
    
    if (masterPassword.length < 12) {
        showToast('Master password must be at least 12 characters', 'error');
        return;
    }
    
    try {
        const response = await fetch(`${API_URL}/vault/create`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                master_password: masterPassword
            })
        });
        
        const data = await response.json();
        
        if (response.ok) {
            currentVault.isLocked = false;
            currentVault.masterPassword = masterPassword;
            currentVault.passwords = [];
            currentVault.metadata = data.metadata;
            
            showToast('Vault created successfully!', 'success');
            updateUI();
        } else {
            showToast(data.error || 'Failed to create vault', 'error');
        }
    } catch (error) {
        console.error('Error:', error);
        showToast('Error connecting to server. Make sure the backend is running.', 'error');
    }
}

// Unlock vault
async function unlockVault() {
    const masterPassword = document.getElementById('masterPassword').value;
    
    if (!masterPassword) {
        showToast('Please enter your master password', 'error');
        return;
    }
    
    try {
        const response = await fetch(`${API_URL}/vault/unlock`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                master_password: masterPassword
            })
        });
        
        const data = await response.json();
        
        if (response.ok) {
            currentVault.isLocked = false;
            currentVault.masterPassword = masterPassword;
            currentVault.passwords = data.passwords || [];
            currentVault.honeyAccounts = data.honey_accounts || [];
            currentVault.metadata = data.metadata;
            
            showToast('Vault unlocked successfully!', 'success');
            updateUI();
            renderPasswords();
        } else {
            showToast(data.error || 'Failed to unlock vault', 'error');
        }
    } catch (error) {
        console.error('Error:', error);
        showToast('Error connecting to server. Make sure the backend is running.', 'error');
    }
}

// Lock vault
function lockVault() {
    if (confirm('Are you sure you want to lock the vault?')) {
        currentVault.isLocked = true;
        currentVault.masterPassword = null;
        currentVault.passwords = [];
        currentVault.honeyAccounts = [];
        
        document.getElementById('masterPassword').value = '';
        showToast('Vault locked', 'info');
        updateUI();
    }
}

// Add password
async function addPassword() {
    const website = document.getElementById('website').value;
    const username = document.getElementById('username').value;
    const password = document.getElementById('password').value;
    
    if (!website || !username || !password) {
        showToast('Please fill in all fields', 'error');
        return;
    }
    
    try {
        const response = await fetch(`${API_URL}/vault/add-password`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                master_password: currentVault.masterPassword,
                website: website,
                username: username,
                password: password
            })
        });
        
        const data = await response.json();
        
        if (response.ok) {
            currentVault.passwords.push({
                website: website,
                username: username,
                password: password
            });
            
            // Clear form
            document.getElementById('website').value = '';
            document.getElementById('username').value = '';
            document.getElementById('password').value = '';
            
            showToast('Password added successfully!', 'success');
            renderPasswords();
        } else {
            showToast(data.error || 'Failed to add password', 'error');
        }
    } catch (error) {
        console.error('Error:', error);
        showToast('Error connecting to server', 'error');
    }
}

// Generate strong password
function generatePassword() {
    const length = 16;
    const charset = 'abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789!@#$%^&*()_+-=[]{}|;:,.<>?';
    let password = '';
    
    // Ensure at least one of each type
    password += 'ABCDEFGHIJKLMNOPQRSTUVWXYZ'[Math.floor(Math.random() * 26)];
    password += 'abcdefghijklmnopqrstuvwxyz'[Math.floor(Math.random() * 26)];
    password += '0123456789'[Math.floor(Math.random() * 10)];
    password += '!@#$%^&*()_+-='[Math.floor(Math.random() * 14)];
    
    // Fill the rest
    for (let i = password.length; i < length; i++) {
        password += charset[Math.floor(Math.random() * charset.length)];
    }
    
    // Shuffle
    password = password.split('').sort(() => Math.random() - 0.5).join('');
    
    document.getElementById('password').value = password;
    document.getElementById('password').type = 'text';
    
    showToast('Strong password generated!', 'success');
}

// Render passwords in the list
function renderPasswords() {
    const passwordList = document.getElementById('passwordList');
    const passwordCount = document.getElementById('passwordCount');
    
    if (currentVault.passwords.length === 0) {
        passwordList.innerHTML = '<p style="text-align: center; color: var(--text-secondary); padding: 40px;">No passwords yet. Add your first password above!</p>';
        passwordCount.textContent = '0 passwords';
        return;
    }
    
    passwordCount.textContent = `${currentVault.passwords.length} password${currentVault.passwords.length !== 1 ? 's' : ''}`;
    
    passwordList.innerHTML = currentVault.passwords.map((entry, index) => `
        <div class="password-item" data-index="${index}">
            <div class="password-item-header">
                <div>
                    <div class="password-item-website">🌐 ${escapeHtml(entry.website)}</div>
                    <div class="password-item-username">👤 ${escapeHtml(entry.username)}</div>
                </div>
                <div class="password-item-actions">
                    <button class="action-btn" onclick="copyPassword(${index})" title="Copy password">📋</button>
                    <button class="action-btn" onclick="showPassword(${index})" title="View password">👁️</button>
                    <button class="action-btn" onclick="deletePassword(${index})" title="Delete">🗑️</button>
                </div>
            </div>
        </div>
    `).join('');
}

// Search passwords
function searchPasswords() {
    const searchTerm = document.getElementById('searchInput').value.toLowerCase();
    const items = document.querySelectorAll('.password-item');
    
    items.forEach(item => {
        const index = item.getAttribute('data-index');
        const entry = currentVault.passwords[index];
        const matches = entry.website.toLowerCase().includes(searchTerm) || 
                       entry.username.toLowerCase().includes(searchTerm);
        
        item.style.display = matches ? 'block' : 'none';
    });
}

// Copy password to clipboard
function copyPassword(index) {
    const password = currentVault.passwords[index].password;
    
    navigator.clipboard.writeText(password).then(() => {
        showToast('Password copied to clipboard!', 'success');
    }).catch(err => {
        showToast('Failed to copy password', 'error');
    });
}

// Show password in modal
function showPassword(index) {
    const entry = currentVault.passwords[index];
    const modal = document.getElementById('passwordModal');
    const modalTitle = document.getElementById('modalTitle');
    const modalBody = document.getElementById('modalBody');
    
    modalTitle.textContent = `Password for ${entry.website}`;
    modalBody.innerHTML = `
        <div style="margin: 20px 0;">
            <p><strong>Website:</strong> ${escapeHtml(entry.website)}</p>
            <p><strong>Username:</strong> ${escapeHtml(entry.username)}</p>
            <p><strong>Password:</strong> <code style="background: #f1f5f9; padding: 5px 10px; border-radius: 4px; font-family: monospace;">${escapeHtml(entry.password)}</code></p>
        </div>
        <div class="button-group">
            <button class="btn btn-primary" onclick="copyPassword(${index}); closeModal();">📋 Copy Password</button>
            <button class="btn btn-secondary" onclick="closeModal()">Close</button>
        </div>
    `;
    
    modal.style.display = 'block';
}

// Delete password
function deletePassword(index) {
    if (confirm('Are you sure you want to delete this password?')) {
        currentVault.passwords.splice(index, 1);
        showToast('Password deleted', 'info');
        renderPasswords();
    }
}

// Generate honey accounts
async function generateHoneyAccounts() {
    try {
        const response = await fetch(`${API_URL}/honey/generate`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                count: 10
            })
        });
        
        const data = await response.json();
        
        if (response.ok) {
            currentVault.honeyAccounts = data.honey_accounts;
            showToast(`Generated ${data.honey_accounts.length} honey accounts`, 'success');
        } else {
            showToast(data.error || 'Failed to generate honey accounts', 'error');
        }
    } catch (error) {
        console.error('Error:', error);
        showToast('Error connecting to server', 'error');
    }
}

// Show honey accounts
function showHoneyAccounts() {
    const list = document.getElementById('honeyAccountsList');
    
    if (currentVault.honeyAccounts.length === 0) {
        showToast('No honey accounts yet. Generate some first!', 'info');
        return;
    }
    
    list.classList.toggle('hidden');
    
    if (!list.classList.contains('hidden')) {
        list.innerHTML = currentVault.honeyAccounts.map((account, index) => `
            <div class="honey-account-item">
                <strong>🍯 Honey Account #${index + 1}</strong><br>
                Website: ${escapeHtml(account.website)}<br>
                Username: ${escapeHtml(account.username)}<br>
                <small style="color: var(--text-secondary);">Any login to this account will trigger a breach alert!</small>
            </div>
        `).join('');
    }
}

// Export vault
async function exportVault() {
    try {
        const vaultData = {
            passwords: currentVault.passwords,
            honeyAccounts: currentVault.honeyAccounts,
            exportDate: new Date().toISOString()
        };
        
        const dataStr = JSON.stringify(vaultData, null, 2);
        const dataBlob = new Blob([dataStr], { type: 'application/json' });
        const url = URL.createObjectURL(dataBlob);
        
        const link = document.createElement('a');
        link.href = url;
        link.download = `guardlocker_vault_${Date.now()}.json`;
        link.click();
        
        showToast('Vault exported successfully!', 'success');
    } catch (error) {
        showToast('Failed to export vault', 'error');
    }
}

// Import vault
function importVault() {
    const input = document.createElement('input');
    input.type = 'file';
    input.accept = '.json';
    
    input.onchange = function(e) {
        const file = e.target.files[0];
        const reader = new FileReader();
        
        reader.onload = function(event) {
            try {
                const vaultData = JSON.parse(event.target.result);
                
                if (confirm(`Import ${vaultData.passwords.length} passwords? This will merge with your current vault.`)) {
                    currentVault.passwords = [...currentVault.passwords, ...vaultData.passwords];
                    if (vaultData.honeyAccounts) {
                        currentVault.honeyAccounts = [...currentVault.honeyAccounts, ...vaultData.honeyAccounts];
                    }
                    
                    renderPasswords();
                    showToast('Vault imported successfully!', 'success');
                }
            } catch (error) {
                showToast('Invalid vault file', 'error');
            }
        };
        
        reader.readAsText(file);
    };
    
    input.click();
}

// Update UI based on vault state
function updateUI() {
    const authSection = document.getElementById('authSection');
    const vaultSection = document.getElementById('vaultSection');
    const statusIndicator = document.getElementById('statusIndicator');
    const statusText = document.getElementById('statusText');
    
    if (currentVault.isLocked) {
        authSection.classList.remove('hidden');
        vaultSection.classList.add('hidden');
        statusIndicator.className = 'status-indicator locked';
        statusText.textContent = 'Vault Locked';
    } else {
        authSection.classList.add('hidden');
        vaultSection.classList.remove('hidden');
        statusIndicator.className = 'status-indicator unlocked';
        statusText.textContent = 'Vault Unlocked';
    }
}

// Close modal
function closeModal() {
    document.getElementById('passwordModal').style.display = 'none';
}

// Close modal when clicking outside
window.onclick = function(event) {
    const modal = document.getElementById('passwordModal');
    if (event.target === modal) {
        modal.style.display = 'none';
    }
}

// Show toast notification
function showToast(message, type = 'info') {
    const toast = document.getElementById('toast');
    toast.textContent = message;
    toast.className = `toast ${type}`;
    toast.style.display = 'block';
    
    setTimeout(() => {
        toast.style.display = 'none';
    }, 3000);
}

// Show about modal
function showAbout() {
    const modal = document.getElementById('passwordModal');
    const modalTitle = document.getElementById('modalTitle');
    const modalBody = document.getElementById('modalBody');
    
    modalTitle.textContent = 'About GuardLocker';
    modalBody.innerHTML = `
        <div style="line-height: 1.8;">
            <h3>🔒 GuardLocker v1.0</h3>
            <p>Advanced Honey Password Vault based on USENIX Security 2025 research.</p>
            
            <h4>Key Features:</h4>
            <ul>
                <li>🍯 Honey Encryption - Plausible decoy vaults</li>
                <li>🤖 AI-Powered - 85M parameter Transformer model</li>
                <li>🔍 Breach Detection - Automatic honey account monitoring</li>
                <li>🛡️ Defense in Depth - Multiple security layers</li>
                <li>⚡ Efficient - Optimized for speed</li>
            </ul>
            
            <p><strong>Research:</strong> "Practically Secure Honey Password Vaults: New Design and New Evaluation against Online Guessing" by Haibo Cheng et al., USENIX Security 2025</p>
            
            <button class="btn btn-secondary" onclick="closeModal()">Close</button>
        </div>
    `;
    
    modal.style.display = 'block';
}

// Show documentation
function showDocumentation() {
    const modal = document.getElementById('passwordModal');
    const modalTitle = document.getElementById('modalTitle');
    const modalBody = document.getElementById('modalBody');
    
    modalTitle.textContent = 'Documentation';
    modalBody.innerHTML = `
        <div style="line-height: 1.8;">
            <h3>📚 How to Use GuardLocker</h3>
            
            <h4>Getting Started:</h4>
            <ol>
                <li>Create a strong master password (12+ characters)</li>
                <li>Click "Create New Vault" or "Unlock Vault"</li>
                <li>Add your passwords using the form</li>
                <li>Generate honey accounts for breach detection</li>
            </ol>
            
            <h4>Security Best Practices:</h4>
            <ul>
                <li>Use a unique, strong master password</li>
                <li>Generate 10-20 honey accounts</li>
                <li>Export backups regularly</li>
                <li>Monitor honey account alerts</li>
            </ul>
            
            <h4>Features:</h4>
            <ul>
                <li>📋 Copy passwords to clipboard</li>
                <li>🔍 Search your vault</li>
                <li>📤 Export/Import vaults</li>
                <li>🎲 Generate strong passwords</li>
            </ul>
            
            <button class="btn btn-secondary" onclick="closeModal()">Close</button>
        </div>
    `;
    
    modal.style.display = 'block';
}

// Escape HTML to prevent XSS
function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}