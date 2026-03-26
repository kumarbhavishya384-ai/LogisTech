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
            const status = usage > 90 ? '<span class="badge badge-warning">Critical</span>' : '<span class="badge badge-success">Optimal</span>';
            
            row.innerHTML = `
                <td><strong>${wh.location}</strong><br><small style="color:var(--text-dim); text-transform: uppercase;">${wh.id}</small></td>
                <td>${JSON.stringify(wh.inventory).replace(/[{}"]/g, '') || "Empty"}</td>
                <td>
                    <div style="font-size: 0.8rem; margin-bottom: 5px;">${usage}% (${totalInv}/${wh.capacity})</div>
                    <div class="progress-bar"><div class="progress-fill" style="width: ${usage}%; background: ${usage > 80 ? 'var(--secondary)' : 'var(--primary)'}"></div></div>
                </td>
                <td>${status}</td>
            `;
            table.appendChild(row);
        });

        const successRate = (state.total_revenue / 50.0) / Math.max(1, (state.total_revenue / 50.0 + state.unfilled_orders)) * 100;
        const successRateId = document.getElementById('success-rate');
        if (successRateId) successRateId.textContent = successRate.toFixed(1);
    } catch (e) {}
}

function clearAllData() {
    if(!confirm("Are you sure you want to wipe all Intelligence Visualization data?")) return;
    document.querySelectorAll('.dummy-row').forEach(r => r.remove());
    document.getElementById('node-registry').innerHTML = '';
    document.getElementById('freight-manifest').innerHTML = '';
    alert("Simulation Grid Cleared. You can now enter your own tactical data.");
}

function registerUserNode() {
    const id = document.getElementById('reg-id').value;
    const loc = document.getElementById('reg-loc').value;
    const cap = document.getElementById('reg-cap').value;
    if(!id || !loc || !cap) return alert("Please fill all fields.");

    const row = document.createElement('tr');
    row.className = 'user-row';
    row.innerHTML = `<td><strong>${id}</strong></td><td>${loc}</td><td>${cap}</td><td><span class="badge badge-success">User Node</span></td>`;
    document.getElementById('node-registry').appendChild(row);
    alert(`Success: Hub ${id} deployed to global registry.`);
}

function dispatchUserOrder() {
    const id = document.getElementById('f-id').value;
    const route = document.getElementById('f-route').value;
    const nodes = document.getElementById('f-nodes').value;
    if(!id || !route || !nodes) return alert("Fill dispatch manifest first.");

    const row = document.createElement('tr');
    row.className = 'user-row success-row';
    row.innerHTML = `<td>#${id}</td><td>${nodes}</td><td>${route}</td><td><span class="badge badge-success">Dispatched</span></td>`;
    document.getElementById('freight-manifest').appendChild(row);
    alert(`Order #${id} dispatched to logistics network.`);
}

function switchTab(tab) {
    // 1. Reset all views and nav items
    document.querySelectorAll('.tab-view').forEach(v => v.classList.remove('active'));
    document.querySelectorAll('.nav-item').forEach(v => v.classList.remove('active'));
    
    // 2. Identify and activate the target view
    const targetView = document.getElementById(`tab-${tab}`);
    if (targetView) targetView.classList.add('active');

    // 3. Highlight the correct sidebar item
    // We use a query selector to find the exact tab clicked
    const clickedItem = Array.from(document.querySelectorAll('.nav-item')).find(item => item.getAttribute('onclick')?.includes(tab));
    if (clickedItem) clickedItem.classList.add('active');

    // 4. Update the Strategic Titles
    const titles = {
        'map': ['Global Operations Dashboard', 'Live monitoring of supply chain network'],
        'wh': ['Warehouse Network Manager', 'Strategic expansion and capacity oversight'],
        'freight': ['Freight Logistics Terminal', 'Active manifest and global shipment tracking'],
        'insights': ['Market Intelligence AI', 'Predictive demand and route optimization'],
        'eval': ['Agent Evaluation Matrix', 'Performance analysis benchmarks']
    };
    
    const titleEl = document.getElementById('view-title');
    const taglineEl = document.getElementById('view-tagline');
    
    if (titleEl && titles[tab]) titleEl.textContent = titles[tab][0];
    if (taglineEl && titles[tab]) taglineEl.textContent = titles[tab][1];

    // 5. Initialize specialized tab features
    if (tab === 'insights') initInsightsChart();
    
    // 6. Manual update of stats if in Map view
    if (tab === 'map') updateStats();

    console.log(`Navigation: Switched to ${tab} view.`);
}

let chart = null;
function initInsightsChart() {
    const ctx = document.getElementById('demandChart');
    if (!ctx || chart) return;
    chart = new Chart(ctx, {
        type: 'line',
        data: {
            labels: ['Day 1', 'Day 5', 'Day 10', 'Day 15', 'Day 20', 'Day 25', 'Day 30'],
            datasets: [{
                label: 'Global SKU Demand',
                data: [420, 580, 890, 1100, 950, 1300, 1550],
                borderColor: '#6366f1',
                backgroundColor: 'rgba(99, 102, 241, 0.1)',
                tension: 0.4,
                fill: true
            }]
        },
        options: {
            responsive: true,
            plugins: { legend: { display: false } },
            scales: { y: { grid: { color: 'rgba(255,255,255,0.05)' } }, x: { grid: { display: false } } }
        }
    });
}

setInterval(updateStats, 3000);
updateStats();
