async function loadBranches() {
    try {
        const res = await fetch('/api/stats/by-branch');
        const data = await res.json();
        const sel = document.getElementById('branch-select');
        data.forEach(b => {
            const opt = document.createElement('option');
            opt.value = b.branch_id;
            opt.textContent = `${b.branch_name} (${b.province})`;
            sel.appendChild(opt);
        });
    } catch (e) {
        console.error('branches error:', e);
    }
}

async function loadPending() {
    const branchId = document.getElementById('branch-select').value;
    if (!branchId) return;

    try {
        const res = await fetch(`/api/branch/${branchId}/pending`);
        const data = await res.json();
        const tbody = document.querySelector('#pending-table tbody');
        const empty = document.getElementById('pending-empty');
        tbody.innerHTML = '';

        if (data.length === 0) {
            empty.style.display = 'block';
            return;
        }
        empty.style.display = 'none';

        data.forEach(r => {
            const flags = (r.flags || []).map(f => `<span class="flag-badge">${f}</span>`).join(' ');
            tbody.innerHTML += `
                <tr>
                    <td>${r.id}</td>
                    <td>${r.type}</td>
                    <td>${r.name}</td>
                    <td>${r.minutes}</td>
                    <td>${r.date}</td>
                    <td>${flags}</td>
                    <td>
                        <button class="btn-approve" onclick="approve(${r.id})">อนุมัติ</button>
                        <button class="btn-reject" onclick="reject(${r.id})">ปฏิเสธ</button>
                    </td>
                </tr>`;
        });
    } catch (e) {
        console.error('pending error:', e);
    }
}

async function approve(id) {
    await fetch(`/api/records/${id}/approve`, {
        method: 'PATCH',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({approved_by: 'สาขา Admin'})
    });
    loadPending();
}

async function reject(id) {
    const reason = prompt('เหตุผลที่ปฏิเสธ:');
    if (!reason) return;
    await fetch(`/api/records/${id}/reject`, {
        method: 'PATCH',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({reason})
    });
    loadPending();
}

loadBranches();
