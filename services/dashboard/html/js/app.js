const FMT = new Intl.NumberFormat('th-TH');
const DATE_FMT = new Intl.DateTimeFormat('th-TH', { year: 'numeric', month: 'long', day: 'numeric' });

function formatThaiDate(str) {
    if (!str) return '-';
    return DATE_FMT.format(new Date(str));
}

async function loadStats() {
    try {
        const res = await fetch('/api/stats/total');
        const data = await res.json();
        animateCounter(data.total_minutes);
        updateProgress(data.total_minutes);
    } catch (e) {
        console.error('stats error:', e);
    }
}

function animateCounter(target) {
    const el = document.getElementById('grand-counter');
    const start = parseInt(el.textContent.replace(/,/g, '')) || 0;
    const diff = target - start;
    const steps = 60;
    let step = 0;

    function tick() {
        step++;
        const val = Math.floor(start + (diff * step / steps));
        el.textContent = FMT.format(val);
        if (step < steps) requestAnimationFrame(tick);
        else el.textContent = FMT.format(target);
    }
    tick();
}

function updateProgress(current) {
    const target = 49000000;
    const pct = Math.min((current / target) * 100, 100);
    document.getElementById('progress-fill').style.width = pct + '%';
    document.getElementById('progress-text').textContent = pct.toFixed(2) + '%';
}

async function loadProjection() {
    try {
        const res = await fetch('/api/projection');
        const d = await res.json();

        document.getElementById('date-start').textContent = formatThaiDate(d.start_date);
        document.getElementById('date-today').textContent = formatThaiDate(d.today);
        document.getElementById('date-end').textContent = formatThaiDate(d.deadline);

        document.getElementById('proj-date').textContent = d.estimated_completion_date ? formatThaiDate(d.estimated_completion_date) : '-';
        document.getElementById('proj-needed').textContent = FMT.format(d.daily_rate_needed);
        document.getElementById('proj-current').textContent = FMT.format(d.daily_rate_current);
        document.getElementById('proj-days').textContent = d.days_remaining;

        const statusEl = document.getElementById('proj-status');
        if (d.on_track) {
            statusEl.textContent = 'ทันกำหนด!';
            statusEl.className = 'proj-status on-track';
        } else {
            statusEl.textContent = 'ต้องเร่งเพิ่ม';
            statusEl.className = 'proj-status off-track';
        }
    } catch (e) {
        console.error('projection error:', e);
    }
}

async function loadLeaderboard(type, btn) {
    // Toggle active button
    if (btn) {
        btn.parentElement.querySelectorAll('button').forEach(b => b.classList.remove('active'));
        btn.classList.add('active');
    }

    try {
        const res = await fetch(`/api/leaderboard?type=${type}&limit=10`);
        const data = await res.json();
        const tbody = document.querySelector('#leaderboard-table tbody');
        tbody.innerHTML = '';

        data.forEach(item => {
            const name = type === 'branch' ? item.branch_name : item.name;
            tbody.innerHTML += `<tr><td>${item.rank}</td><td>${name}</td><td>${FMT.format(item.minutes)}</td></tr>`;
        });
    } catch (e) {
        console.error('leaderboard error:', e);
    }
}

// Init
loadStats();
loadProjection();
loadLeaderboard('branch');

// Auto-refresh every 30s
setInterval(() => {
    loadStats();
    loadProjection();
}, 30000);
