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

        const projDateEl = document.getElementById('proj-date');
        if (d.estimated_completion_date) {
            projDateEl.textContent = formatThaiDate(d.estimated_completion_date);
        } else if (d.current_minutes >= d.target_minutes) {
            projDateEl.textContent = 'ครบเป้าแล้ว!';
        } else {
            projDateEl.textContent = 'ยังประเมินไม่ได้';
        }

        document.getElementById('proj-needed').textContent = FMT.format(d.daily_rate_needed);
        document.getElementById('proj-current').textContent = FMT.format(d.daily_rate_current);
        document.getElementById('proj-days').textContent = d.days_remaining;

        const statusEl = document.getElementById('proj-status');
        if (d.current_minutes >= d.target_minutes) {
            statusEl.textContent = 'ครบเป้าแล้ว!';
            statusEl.className = 'proj-status on-track';
        } else if (d.on_track) {
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

async function loadProvinceTable(view, btn) {
    if (btn) {
        btn.parentElement.querySelectorAll('button').forEach(b => b.classList.remove('active'));
        btn.classList.add('active');
    }

    const thead = document.getElementById('province-table-head');
    const tbody = document.getElementById('province-table-body');
    tbody.innerHTML = '';

    try {
        if (view === 'province') {
            thead.innerHTML = '<tr><th>#</th><th>จังหวัด</th><th>นาที</th><th>รายการ</th></tr>';
            const res = await fetch('/api/stats/by-province');
            const data = await res.json();
            data.forEach((d, i) => {
                tbody.innerHTML += `<tr><td>${i + 1}</td><td>${d.province}</td><td>${FMT.format(d.minutes)}</td><td>${FMT.format(d.records)}</td></tr>`;
            });
        } else if (view === 'group') {
            thead.innerHTML = '<tr><th>#</th><th>กลุ่ม</th><th>จังหวัด</th><th>สาขา</th><th>นาที</th></tr>';
            const res = await fetch('/api/stats/by-group');
            const data = await res.json();
            data.forEach((d, i) => {
                tbody.innerHTML += `<tr><td>${i + 1}</td><td>${d.group_name}</td><td>${d.provinces.join(', ')}</td><td>${d.branches_count}</td><td>${FMT.format(d.minutes)}</td></tr>`;
            });
        } else if (view === 'markers') {
            thead.innerHTML = '<tr><th>#</th><th>สาขา</th><th>จังหวัด</th><th>พิกัด</th><th>นาที</th><th>รายการ</th></tr>';
            const res = await fetch('/api/markers');
            const data = await res.json();
            const branches = data.filter(m => m.type === 'branch');
            branches.sort((a, b) => b.minutes - a.minutes);
            branches.forEach((d, i) => {
                const gps = `${d.lat.toFixed(4)}, ${d.lng.toFixed(4)}`;
                tbody.innerHTML += `<tr><td>${i + 1}</td><td>${d.name}</td><td>${d.province}</td><td><code>${gps}</code></td><td>${FMT.format(d.minutes)}</td><td>${FMT.format(d.records)}</td></tr>`;
            });
        }
    } catch (e) {
        console.error('province table error:', e);
    }
}

// Init
loadStats();
loadProjection();
loadLeaderboard('branch');
loadProvinceTable('province');

// Auto-refresh every 30s
setInterval(() => {
    loadStats();
    loadProjection();
}, 30000);
