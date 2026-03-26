const BASE_URL = window.location.origin;
let sessionId = localStorage.getItem('session_id') || "";
let config = null;
let currentOtpMode = 'register';

async function initEmailJS() {
    const res = await fetch(`${BASE_URL}/config`);
    config = await res.json();
    emailjs.init(config.EMAILJS_PUBLIC_KEY);
}
initEmailJS();

async function auth(type) {
    if (type === 'login') {
        const email = document.getElementById('l-email').value;
        const pass = document.getElementById('l-pass').value;
        let res = await fetch(`${BASE_URL}/auth/login`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ email: email, password: pass })
        });
        if (res.ok) {
            const data = await res.json();
            localStorage.setItem('token', data.access_token);
            localStorage.setItem('user', data.full_name);
            window.location.href = '/dashboard';
        } else {
            const err = await res.json();
            alert(err.detail || 'Invalid email or password');
        }
    }
}

async function requestOtp(mode = 'register') {
    currentOtpMode = mode;
    const email = document.getElementById(mode === 'register' ? 'r-email' : 'f-email').value;
    if(!email) return alert("Please enter email first.");
    try {
        const res = await fetch(`${BASE_URL}/auth/otp/generate`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ email: email })
        });
        const { otp } = await res.json();
        await emailjs.send(config.EMAILJS_SERVICE_ID, config.EMAILJS_TEMPLATE_OTP, {
            email: email, passcode: otp, time: new Date(Date.now() + 15 * 60000).toLocaleTimeString()
        });
        document.getElementById('otp-modal').style.display = 'flex';
        if(mode === 'forgot') {
            document.getElementById('forgot-pass-group').style.display = 'block';
            document.getElementById('forgot-btn').textContent = "Verify & Update Password";
        }
    } catch(e) {
        alert("Failed to send OTP.");
    }
}

async function verifyAndSubmit() {
    const otp = document.getElementById('otp-input').value;
    if(!otp) return alert("Enter OTP");
    if (currentOtpMode === 'register') {
        const name = document.getElementById('r-name').value;
        const email = document.getElementById('r-email').value;
        const pass = document.getElementById('r-pass').value;
        const res = await fetch(`${BASE_URL}/auth/register`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ name: name, email: email, password: pass, otp: otp })
        });
        if (res.ok) {
            await emailjs.send(config.EMAILJS_SERVICE_ID, config.EMAILJS_TEMPLATE_WELCOME, { email: email, name: name });
            alert('Verification Successful! Login now.');
            location.reload();
        } else {
            const err = await res.json();
            alert(err.detail || 'Verification failed');
        }
    } else {
        const email = document.getElementById('f-email').value;
        const pass = document.getElementById('f-new-pass').value;
        const res = await fetch(`${BASE_URL}/auth/forgot-password`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ email: email, password: pass, otp: otp })
        });
        if (res.ok) {
            alert('Password updated successfully!');
            location.reload();
        } else {
            const err = await res.json();
            alert(err.detail || 'Update failed');
        }
    }
}

function logout() {
    localStorage.removeItem('user');
    window.location.href = '/';
}

async function addBranch() {
    const id = document.getElementById('new-wh-id').value;
    const loc = document.getElementById('new-wh-loc').value;
    const cap = parseInt(document.getElementById('new-wh-cap').value);
    const res = await fetch(`${BASE_URL}/add-branch`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ session_id: sessionId, wh_id: id, location: loc, capacity: cap })
    });
    if(res.ok) {
        alert(`New branch ${id} added!`);
        updateStats();
    }
}

async function createShipment() {
    const sku = document.getElementById('ship-sku').value;
    const origin = document.getElementById('ship-origin').value;
    const dest = document.getElementById('ship-dest').value;
    const qty = parseInt(document.getElementById('ship-qty').value);
    const res = await fetch(`${BASE_URL}/step?session_id=${sessionId}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ action_type: "TRANSFER", params: { sku: sku, origin: origin, destination: dest, quantity: qty } })
    });
    if(res.ok) {
        alert(`Shipment ${sku} created!`);
        updateStats();
    }
}

async function startTask() {
    const task = document.getElementById('task-select').value;
    const res = await fetch(`${BASE_URL}/reset?task_id=${task}`, { method: 'POST' });
    const data = await res.json();
    sessionId = data.session_id;
    localStorage.setItem('session_id', sessionId);
    alert(`Environment Started!`);
    updateStats();
}

async function updateStats() {
    if (!sessionId) return;
    try {
        const res = await fetch(`${BASE_URL}/state?session_id=${sessionId}`);
        const state = await res.json();
        document.getElementById('cash-bal').textContent = state.cash_balance.toFixed(2);
        document.getElementById('revenue').textContent = state.total_revenue.toFixed(2);
        document.getElementById('unfilled').textContent = state.unfilled_orders;
        document.getElementById('current-day').textContent = `DAY ${state.current_day}`;
        const table = document.getElementById('inventory-table');
        if (!table) return;
        table.innerHTML = '';
        Object.values(state.warehouses).forEach(wh => {
            const row = document.createElement('tr');
            const totalInv = Object.values(wh.inventory).reduce((a, b) => a + b, 0);
            const usage = (totalInv / wh.capacity * 100).toFixed(1);
            row.innerHTML = `<td><strong>${wh.location}</strong><br><small>${wh.id}</small></td><td>${JSON.stringify(wh.inventory).replace(/[{}"]/g, '')}</td><td><div class="progress-bar"><div class="progress-fill" style="width: ${usage}%; background: ${usage > 80 ? 'var(--secondary)' : 'var(--primary)'}"></div></div></td><td><button class="badge badge-success">Manage</button></td>`;
            table.appendChild(row);
        });
    } catch (e) {}
}
