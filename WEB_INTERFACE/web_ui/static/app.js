// GuardLocker v2 — Application JS
// Security note: failed_attempts counter is INTENTIONALLY hidden from UI.
// An attacker watching the screen would see "0 failed attempts" on decoy vault
// and realise they failed. Telegram alerts handle legitimate owner notification.

const API = 'http://localhost:5000/api';

let vault = {
    locked:         true,
    masterPassword: null,
    passwords:      [],
    honeyAccounts:  [],
    metadata:       null,
    isDecoy:        false,
};

// ═══════════════════════════════════════════════
// THEME
// ═══════════════════════════════════════════════
function toggleTheme() {
    const html  = document.documentElement;
    const next  = html.getAttribute('data-theme') === 'dark' ? 'light' : 'dark';
    html.setAttribute('data-theme', next);
    try { localStorage.setItem('gl-theme', next); } catch(_) {}
}

function loadTheme() {
    try {
        const saved = localStorage.getItem('gl-theme');
        if (saved) document.documentElement.setAttribute('data-theme', saved);
    } catch(_) {}
}

// ═══════════════════════════════════════════════
// INIT
// ═══════════════════════════════════════════════
document.addEventListener('DOMContentLoaded', () => {
    loadTheme();
    setupStrengthMeter();
    setDot('locked');
    pollStatus();
    setInterval(pollStatus, 12000);
});

// ═══════════════════════════════════════════════
// STATUS POLL — intentionally omits failed_attempts
// ═══════════════════════════════════════════════
async function pollStatus() {
    try {
        const r = await fetch(`${API}/status`);
        if (!r.ok) return;
        const d = await r.json();

        // Telegram chip
        const chip = document.getElementById('telegramChip');
        const tval = document.getElementById('telegramStatusVal');
        if (d.telegram_alerts) {
            chip?.setAttribute('class','chip chip-green');
            if (chip) chip.textContent = 'Telegram ✓';
            if (tval) { tval.textContent='Active'; tval.className='stat-val v-green'; }
        } else {
            chip?.setAttribute('class','chip chip-amber');
            if (chip) chip.textContent = 'Telegram ○';
            if (tval) { tval.textContent='Not configured'; tval.className='stat-val v-amber'; }
        }

        // Status meta — NO failed attempt count shown
        const meta = document.getElementById('statusMeta');
        if (meta) {
            meta.textContent = d.vault_created
                ? `${d.password_count} password(s) · Argon2id KDF`
                : 'No vault loaded';
        }

    } catch(_) {}
}

// ═══════════════════════════════════════════════
// STATUS DOT
// ═══════════════════════════════════════════════
function setDot(state) {
    const dot  = document.getElementById('statusDot');
    const text = document.getElementById('statusText');
    if (!dot) return;
    dot.setAttribute('data-state', state);
    const labels = { locked:'Vault Locked', open:'Vault Unlocked', working:'Processing…' };
    if (text && labels[state]) text.textContent = labels[state];
}

// ═══════════════════════════════════════════════
// STRENGTH METER
// ═══════════════════════════════════════════════
function setupStrengthMeter() {
    const inp = document.getElementById('masterPassword');
    if (!inp) return;
    inp.addEventListener('input', () => {
        const p    = inp.value;
        const bar  = document.getElementById('strengthBar');
        const hint = document.getElementById('strengthHint');
        if (!bar || !hint) return;
        if (!p) { bar.className='strength-bar'; hint.textContent=''; return; }

        let score = 0;
        if (p.length >= 8)  score++;
        if (p.length >= 12) score++;
        if (p.length >= 16) score++;
        if (/[a-z]/.test(p) && /[A-Z]/.test(p)) score++;
        if (/\d/.test(p))  score++;
        if (/[^a-zA-Z0-9]/.test(p)) score++;

        if (score <= 2) {
            bar.className   = 'strength-bar s-weak';
            hint.textContent = '⚠ Weak — use 12+ chars, mixed case, digits, symbols';
        } else if (score <= 4) {
            bar.className   = 'strength-bar s-medium';
            hint.textContent = '⚡ Medium — add more complexity';
        } else {
            bar.className   = 'strength-bar s-strong';
            hint.textContent = '✓ Strong password';
        }
    });
}

// ═══════════════════════════════════════════════
// TOGGLE PASSWORD VISIBILITY
// ═══════════════════════════════════════════════
function togglePassword(id) {
    const el = document.getElementById(id);
    if (el) el.type = el.type === 'password' ? 'text' : 'password';
}

// ═══════════════════════════════════════════════
// CREATE VAULT
// ═══════════════════════════════════════════════
async function createNewVault() {
    const pw = document.getElementById('masterPassword').value;
    if (!pw)            return showToast('Enter a master password', 'error');
    if (pw.length < 12) return showToast('Password must be ≥ 12 characters', 'error');

    const btn = document.querySelector('[onclick="createNewVault()"]');
    if (btn) btn.classList.add('loading');

    try {
        const r = await fetch(`${API}/vault/create`, {
            method:'POST', headers:{'Content-Type':'application/json'},
            body: JSON.stringify({ master_password: pw })
        });
        const d = await r.json();
        if (r.ok) {
            vault = { locked:false, masterPassword:pw, passwords:[], honeyAccounts:[], metadata:d.metadata, isDecoy:false };
            showToast('Vault created · Argon2id active', 'success');
            updateUI();
        } else {
            showToast(d.error || 'Failed to create vault', 'error');
        }
    } catch(e) { showToast('Cannot reach server — is it running?', 'error'); }
    finally    { if (btn) btn.classList.remove('loading'); }
}

// ═══════════════════════════════════════════════
// UNLOCK VAULT
// ═══════════════════════════════════════════════
async function unlockVault() {
    const pw = document.getElementById('masterPassword').value;
    if (!pw) return showToast('Enter your master password', 'error');

    const btn = document.querySelector('[onclick="unlockVault()"]');
    if (btn) btn.classList.add('loading');
    setDot('working');

    try {
        const r = await fetch(`${API}/vault/unlock`, {
            method:'POST', headers:{'Content-Type':'application/json'},
            body: JSON.stringify({ master_password: pw })
        });
        const d = await r.json();

        if (r.ok) {
            vault.locked         = false;
            vault.masterPassword = pw;
            vault.passwords      = d.passwords      || [];
            vault.honeyAccounts  = d.honey_accounts || [];
            vault.metadata       = d.metadata;
            vault.isDecoy        = !d.is_real;

            // SECURITY: Always show identical success message for real AND decoy.
            // Never reveal real/decoy distinction in UI — attacker may be watching.
            showToast('Vault unlocked', 'success');
            updateUI();
            renderPasswords();
        } else {
            setDot('locked');
            showToast(d.error || 'Failed to unlock', 'error');
        }
    } catch(e) {
        setDot('locked');
        showToast('Cannot reach server — is it running?', 'error');
    }
    finally { if (btn) btn.classList.remove('loading'); }
}

// ═══════════════════════════════════════════════
// LOCK VAULT
// ═══════════════════════════════════════════════
function lockVault() {
    if (!confirm('Lock the vault?')) return;
    vault = { locked:true, masterPassword:null, passwords:[], honeyAccounts:[], metadata:null, isDecoy:false };
    document.getElementById('masterPassword').value = '';
    setDot('locked');
    showToast('Vault locked', 'info');
    updateUI();
}

// ═══════════════════════════════════════════════
// ADD PASSWORD
// ═══════════════════════════════════════════════
async function addPassword() {
    const website  = document.getElementById('website').value.trim();
    const username = document.getElementById('username').value.trim();
    const password = document.getElementById('password').value;
    if (!website || !username || !password) return showToast('Fill in all fields', 'error');

    const btn = document.querySelector('[onclick="addPassword()"]');
    if (btn) btn.classList.add('loading');

    try {
        const r = await fetch(`${API}/vault/add-password`, {
            method:'POST', headers:{'Content-Type':'application/json'},
            body: JSON.stringify({ master_password:vault.masterPassword, website, username, password })
        });
        const d = await r.json();
        if (r.ok) {
            vault.passwords.push({ website, username, password });
            ['website','username','password'].forEach(id => { document.getElementById(id).value = ''; });
            showToast('Password saved', 'success');
            renderPasswords();
        } else {
            showToast(d.error || 'Failed to save', 'error');
        }
    } catch(e) { showToast('Cannot reach server', 'error'); }
    finally    { if (btn) btn.classList.remove('loading'); }
}

// ═══════════════════════════════════════════════
// GENERATE STRONG PASSWORD
// ═══════════════════════════════════════════════
function generatePassword() {
    const lower='abcdefghijklmnopqrstuvwxyz', upper='ABCDEFGHIJKLMNOPQRSTUVWXYZ';
    const digits='0123456789', syms='!@#$%^&*()-_=+';
    const all = lower+upper+digits+syms;
    let pw = [ lower[rand(lower.length)], upper[rand(upper.length)], digits[rand(digits.length)], syms[rand(syms.length)] ];
    for (let i=pw.length; i<18; i++) pw.push(all[rand(all.length)]);
    // Fisher-Yates
    for (let i=pw.length-1;i>0;i--){const j=rand(i+1);[pw[i],pw[j]]=[pw[j],pw[i]];}
    document.getElementById('password').value = pw.join('');
    document.getElementById('password').type  = 'text';
    showToast('Strong password generated', 'success');
}
const rand = n => Math.floor(Math.random()*n);

// ═══════════════════════════════════════════════
// SITE ICONS
// ═══════════════════════════════════════════════
const ICONS = {
    'github':'🐙','gmail':'📧','google':'🔍','facebook':'👤','twitter':'🐦',
    'instagram':'📸','linkedin':'💼','amazon':'🛒','flipkart':'🛍','netflix':'🎬',
    'youtube':'▶️','paytm':'💳','swiggy':'🍔','zomato':'🍕','phonepe':'📱',
    'naukri':'💼','hotstar':'⭐','reddit':'🤖','spotify':'🎵','paypal':'💰',
    'apple':'🍎','discord':'💬','slack':'💬',
};
function siteIcon(site) {
    const s = site.toLowerCase();
    for (const [k,v] of Object.entries(ICONS)) { if (s.includes(k)) return v; }
    return '🌐';
}

// ═══════════════════════════════════════════════
// RENDER PASSWORDS
// ═══════════════════════════════════════════════
function renderPasswords() {
    const list  = document.getElementById('passwordList');
    const count = document.getElementById('passwordCount');
    if (!list) return;

    const n = vault.passwords.length;
    if (count) count.textContent = `${n} password${n!==1?'s':''}`;

    if (n === 0) {
        list.innerHTML = `<div class="empty-state"><div class="empty-icon">🗝</div><p>No passwords yet. Add your first entry above.</p></div>`;
        return;
    }

    list.innerHTML = vault.passwords.map((e,i) => `
        <div class="pwd-item" data-index="${i}">
            <div class="pwd-favicon">${siteIcon(e.website)}</div>
            <div class="pwd-info">
                <div class="pwd-site">${esc(e.website)}</div>
                <div class="pwd-user">${esc(e.username)}</div>
            </div>
            ${e.is_honey_account ? '<span class="honey-tag">🍯 HONEY</span>' : ''}
            <div class="pwd-actions">
                <button class="icon-btn" onclick="copyPwd(${i})" title="Copy">📋</button>
                <button class="icon-btn" onclick="showPwd(${i})" title="View">👁</button>
                <button class="icon-btn" onclick="deletePwd(${i})" title="Delete">🗑</button>
            </div>
        </div>
    `).join('');
}

function searchPasswords() {
    const q = document.getElementById('searchInput').value.toLowerCase();
    document.querySelectorAll('.pwd-item').forEach(el => {
        const e = vault.passwords[el.dataset.index];
        el.style.display = (e.website+e.username).toLowerCase().includes(q) ? '' : 'none';
    });
}

function copyPwd(i) {
    navigator.clipboard.writeText(vault.passwords[i].password)
        .then(()  => showToast('Password copied', 'success'))
        .catch(()  => showToast('Copy failed', 'error'));
}

function showPwd(i) {
    const e = vault.passwords[i];
    showModal(`🌐 ${e.website}`, `
        <div class="detail-row">
            <div class="detail-lbl">Website</div>
            <div class="detail-val">${esc(e.website)}</div>
        </div>
        <div class="detail-row">
            <div class="detail-lbl">Username</div>
            <div class="detail-val">
                ${esc(e.username)}
                <button class="copy-mini" onclick="navigator.clipboard.writeText('${esc(e.username)}');showToast('Copied','success')">copy</button>
            </div>
        </div>
        <div class="detail-row">
            <div class="detail-lbl">Password</div>
            <div class="detail-val">
                <span id="pwdReveal" data-shown="0">${'•'.repeat(Math.min(e.password.length,16))}</span>
                <button class="copy-mini" onclick="toggleReveal(${i})">show</button>
                <button class="copy-mini" onclick="copyPwd(${i});showToast('Copied','success')">copy</button>
            </div>
        </div>
        <div style="margin-top:18px">
            <button class="btn btn-primary btn-sm" onclick="copyPwd(${i});closeModal()">📋 Copy & Close</button>
        </div>
    `);
}

function toggleReveal(i) {
    const el = document.getElementById('pwdReveal'); if (!el) return;
    const p  = vault.passwords[i].password;
    el.dataset.shown = el.dataset.shown==='1'?'0':'1';
    el.textContent   = el.dataset.shown==='1' ? p : '•'.repeat(Math.min(p.length,16));
}

function deletePwd(i) {
    if (!confirm('Delete this entry?')) return;
    vault.passwords.splice(i,1);
    showToast('Entry deleted','info');
    renderPasswords();
}

// ═══════════════════════════════════════════════
// HONEY ACCOUNTS
// ═══════════════════════════════════════════════
async function generateHoneyAccounts() {
    try {
        const r = await fetch(`${API}/honey/generate`, {
            method:'POST', headers:{'Content-Type':'application/json'},
            body: JSON.stringify({ count:10 })
        });
        const d = await r.json();
        if (r.ok) {
            vault.honeyAccounts = d.honey_accounts;
            showToast(`${d.honey_accounts.length} honey accounts generated`, 'success');
        } else { showToast(d.error||'Failed','error'); }
    } catch(e) { showToast('Cannot reach server','error'); }
}

function showHoneyAccounts() {
    const list = document.getElementById('honeyAccountsList');
    if (!list) return;
    if (!vault.honeyAccounts.length) return showToast('Generate honey accounts first','info');
    list.classList.toggle('hidden');
    if (!list.classList.contains('hidden')) {
        list.innerHTML = vault.honeyAccounts.map((a,i) => `
            <div class="honey-item">
                <div class="h-site">🍯 Trap #${i+1} — ${esc(a.website)}</div>
                <div class="h-user">${esc(a.username)}</div>
            </div>
        `).join('');
    }
}

// ═══════════════════════════════════════════════
// TELEGRAM TEST
// ═══════════════════════════════════════════════
async function testTelegram() {
    try {
        const r = await fetch(`${API}/telegram/test`, { method:'POST' });
        const d = await r.json();
        showToast(
            d.success ? '📡 Telegram alert sent!' : '⚠ Telegram not configured',
            d.success ? 'success' : 'warning'
        );
    } catch(e) { showToast('Cannot reach server','error'); }
}

// ═══════════════════════════════════════════════
// BULK GENERATE
// ═══════════════════════════════════════════════
async function bulkGenerate() {
    const count = parseInt(document.getElementById('bulkCount').value)||10000;
    const btn   = document.querySelector('[onclick="bulkGenerate()"]');
    const res   = document.getElementById('bulkResult');

    if (btn) { btn.textContent='⏳ Generating…'; btn.classList.add('loading'); }
    res?.classList.add('hidden');

    try {
        const r = await fetch(`${API}/bulk/generate`, {
            method:'POST', headers:{'Content-Type':'application/json'},
            body: JSON.stringify({ count })
        });
        const d = await r.json();
        if (r.ok && res) {
            res.classList.remove('hidden');
            res.innerHTML = `Generated <span class="hi">${d.count.toLocaleString()}</span> passwords in
                <span class="hi">${d.time_seconds.toFixed(2)}s</span>
                (${Math.round(d.rate_per_second).toLocaleString()} pwd/sec)`;
            showToast(`${d.count.toLocaleString()} passwords generated`,'success');
        } else { showToast(d.error||'Failed','error'); }
    } catch(e) { showToast('Cannot reach server','error'); }
    finally {
        if (btn) { btn.textContent='Generate Dataset'; btn.classList.remove('loading'); }
    }
}

// ═══════════════════════════════════════════════
// EXPORT / IMPORT
// ═══════════════════════════════════════════════
function exportVault() {
    const blob = new Blob([JSON.stringify({
        passwords:vault.passwords, honeyAccounts:vault.honeyAccounts,
        exportDate: new Date().toISOString()
    }, null, 2)], {type:'application/json'});
    const a = Object.assign(document.createElement('a'),{
        href: URL.createObjectURL(blob),
        download: `guardlocker_${Date.now()}.json`
    });
    a.click(); URL.revokeObjectURL(a.href);
    showToast('Vault exported','success');
}

function importVault() {
    const inp = Object.assign(document.createElement('input'),{type:'file',accept:'.json'});
    inp.onchange = e => {
        const fr = new FileReader();
        fr.onload = ev => {
            try {
                const d = JSON.parse(ev.target.result);
                if (confirm(`Import ${d.passwords.length} passwords?`)) {
                    vault.passwords     = [...vault.passwords, ...d.passwords];
                    vault.honeyAccounts = [...vault.honeyAccounts, ...(d.honeyAccounts||[])];
                    renderPasswords();
                    showToast('Vault imported','success');
                }
            } catch(_) { showToast('Invalid vault file','error'); }
        };
        fr.readAsText(e.target.files[0]);
    };
    inp.click();
}

// ═══════════════════════════════════════════════
// UPDATE UI — SECURITY: never expose real vs decoy to screen
// ═══════════════════════════════════════════════
function updateUI() {
    const auth  = document.getElementById('authSection');
    const vsec  = document.getElementById('vaultSection');
    const badge = document.getElementById('vaultTypeBadge');

    if (vault.locked) {
        auth?.classList.remove('hidden');
        vsec?.classList.add('hidden');
        setDot('locked');
    } else {
        auth?.classList.add('hidden');
        vsec?.classList.remove('hidden');
        setDot('open');
        // Always "Vault Active" — never say "Real" or "Decoy"
        if (badge) { badge.textContent = '● Vault Active'; }
    }
}

// ═══════════════════════════════════════════════
// MODAL
// ═══════════════════════════════════════════════
function showModal(title, body) {
    document.getElementById('modalTitle').textContent = title;
    document.getElementById('modalBody').innerHTML    = body;
    document.getElementById('modal').classList.remove('hidden');
}
function closeModal() { document.getElementById('modal').classList.add('hidden'); }

// ═══════════════════════════════════════════════
// TOAST
// ═══════════════════════════════════════════════
let _tt = null;
function showToast(msg, type='info') {
    const t = document.getElementById('toast'); if (!t) return;
    clearTimeout(_tt);
    t.textContent = msg; t.className = `toast ${type}`;
    t.classList.remove('hidden');
    requestAnimationFrame(() => t.classList.add('show'));
    _tt = setTimeout(() => {
        t.classList.remove('show');
        setTimeout(() => t.classList.add('hidden'), 280);
    }, 3400);
}

// ═══════════════════════════════════════════════
// ABOUT
// ═══════════════════════════════════════════════
function showAbout() {
    showModal('About GuardLocker v2', `
        <p style="font-size:13px;color:var(--tx2);line-height:1.7;margin-bottom:16px">
            Honey encryption-based password vault system for Indian users.<br>
            <em>GuardLocker: Argon2id KDF + Indian-Identity Decoy Generation</em><br>
            Lakshya Beria · NIELIT India
        </p>
        <div class="detail-row"><div class="detail-lbl">Key Derivation</div><div class="detail-val">Argon2id · t=3, m=65536 KiB, p=4</div></div>
        <div class="detail-row"><div class="detail-lbl">Encryption</div><div class="detail-val">AES-256-GCM · 96-bit nonce · 256-bit salt</div></div>
        <div class="detail-row"><div class="detail-lbl">Decoy Generator</div><div class="detail-val">Indian Identity v2 · 52.50% classifier accuracy</div></div>
        <div class="detail-row"><div class="detail-lbl">Classifier Baseline</div><div class="detail-val">50.00% (random chance)</div></div>
        <div class="detail-row"><div class="detail-lbl">v1 → v2 Improvement</div><div class="detail-val">66.95% → 52.50% (−14.45 pp)</div></div>
        <div class="detail-row"><div class="detail-lbl">Foundation</div><div class="detail-val">Juels & Ristenpart, EUROCRYPT 2014</div></div>
        <div style="margin-top:18px">
            <button class="btn btn-ghost btn-sm" onclick="closeModal()">Close</button>
        </div>
    `);
}

// ═══════════════════════════════════════════════
// UTILS
// ═══════════════════════════════════════════════
function esc(s) {
    const d = document.createElement('div'); d.textContent=String(s); return d.innerHTML;
}