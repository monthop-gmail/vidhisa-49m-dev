const FMT = new Intl.NumberFormat('th-TH');

async function loadBranches() {
    try {
        const res = await fetch('/api/stats/by-branch');
        const data = await res.json();
        const orgSel = document.getElementById('org-branch');
        data.forEach(b => {
            const opt = document.createElement('option');
            opt.value = b.branch_id;
            opt.textContent = `${b.branch_name} (${b.province})`;
            orgSel.appendChild(opt);
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

async function loadOrganizations() {
    try {
        const res = await fetch('/api/organizations');
        const data = await res.json();
        const tbody = document.querySelector('#org-table tbody');
        tbody.innerHTML = '';
        data.forEach(o => {
            tbody.innerHTML += `
                <tr>
                    <td>${o.id}</td>
                    <td>${o.name}</td>
                    <td>${o.org_type || '-'}</td>
                    <td>${o.province || '-'}</td>
                    <td>${o.branch_id}</td>
                    <td>${FMT.format(o.total_minutes)}</td>
                    <td>${FMT.format(o.total_records)}</td>
                </tr>`;
        });
    } catch (e) {
        console.error('org error:', e);
    }
}

async function createOrg() {
    const body = {
        id: document.getElementById('org-id').value,
        name: document.getElementById('org-name').value,
        org_type: document.getElementById('org-type').value || null,
        branch_id: document.getElementById('org-branch').value || null,
        province: document.getElementById('org-province').value || null,
        latitude: parseFloat(document.getElementById('org-lat').value) || null,
        longitude: parseFloat(document.getElementById('org-lng').value) || null,
        contact: document.getElementById('org-contact').value || null,
    };

    if (!body.id || !body.name) {
        alert('กรุณากรอก รหัส และ ชื่อ');
        return;
    }

    try {
        const res = await fetch('/api/organizations', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify(body),
        });
        if (res.ok) {
            alert('เพิ่มองค์กรสำเร็จ');
            ['org-id','org-name','org-province','org-lat','org-lng','org-contact'].forEach(
                id => document.getElementById(id).value = ''
            );
            loadOrganizations();
        } else {
            const err = await res.json();
            alert(err.detail?.message || 'เกิดข้อผิดพลาด');
        }
    } catch (e) {
        console.error('create org error:', e);
        alert('เกิดข้อผิดพลาด');
    }
}

async function loadBranchTable() {
    try {
        const res = await fetch('/api/branches');
        const data = await res.json();
        const tbody = document.querySelector('#branch-table tbody');
        tbody.innerHTML = '';
        data.forEach(b => {
            tbody.innerHTML += `
                <tr>
                    <td>${b.id}</td>
                    <td>${b.name}</td>
                    <td>${b.group_id || '-'}</td>
                    <td>${b.province}</td>
                    <td>${b.admin_name || '-'}</td>
                    <td>${FMT.format(b.total_minutes)}</td>
                    <td>${FMT.format(b.total_records)}</td>
                </tr>`;
        });
    } catch (e) {
        console.error('branch table error:', e);
    }
}

async function importBranches(input) {
    const file = input.files[0];
    if (!file) return;

    const status = document.getElementById('import-branch-status');
    status.textContent = 'กำลังนำเข้า...';
    status.style.color = '#666';

    try {
        const formData = new FormData();
        formData.append('file', file);
        const res = await fetch('/api/branches/import', {
            method: 'POST',
            body: formData,
        });
        const data = await res.json();
        if (res.ok) {
            status.textContent = data.message;
            status.style.color = '#43a047';
            if (data.errors.length > 0) {
                status.textContent += ' | ' + data.errors.join(', ');
                status.style.color = '#e65100';
            }
            loadBranchTable();
        } else {
            status.textContent = data.detail?.message || 'เกิดข้อผิดพลาด';
            status.style.color = '#e53935';
        }
    } catch (e) {
        console.error('import branches error:', e);
        status.textContent = 'เกิดข้อผิดพลาด';
        status.style.color = '#e53935';
    }
    input.value = '';
}

async function importOrgs(input) {
    const file = input.files[0];
    if (!file) return;

    const status = document.getElementById('import-status');
    status.textContent = 'กำลังนำเข้า...';
    status.style.color = '#666';

    try {
        const formData = new FormData();
        formData.append('file', file);
        const res = await fetch('/api/organizations/import', {
            method: 'POST',
            body: formData,
        });
        const data = await res.json();
        if (res.ok) {
            status.textContent = data.message;
            status.style.color = '#43a047';
            if (data.errors.length > 0) {
                status.textContent += ' | ' + data.errors.join(', ');
                status.style.color = '#e65100';
            }
            loadOrganizations();
        } else {
            status.textContent = data.detail?.message || 'เกิดข้อผิดพลาด';
            status.style.color = '#e53935';
        }
    } catch (e) {
        console.error('import error:', e);
        status.textContent = 'เกิดข้อผิดพลาด';
        status.style.color = '#e53935';
    }
    input.value = '';
}

async function loadParticipants() {
    try {
        const branchId = document.getElementById('participant-branch-filter').value;
        const url = branchId ? `/api/participants?branch_id=${branchId}` : '/api/participants';
        const res = await fetch(url);
        const data = await res.json();
        const tbody = document.querySelector('#participant-table tbody');
        const empty = document.getElementById('participant-empty');
        const count = document.getElementById('participant-count');
        tbody.innerHTML = '';

        count.textContent = `(${data.length} คน)`;

        if (data.length === 0) {
            empty.style.display = 'block';
            return;
        }
        empty.style.display = 'none';

        data.forEach(p => {
            tbody.innerHTML += `
                <tr>
                    <td>${p.id}</td>
                    <td>${p.prefix || '-'}</td>
                    <td>${p.first_name}</td>
                    <td>${p.last_name}</td>
                    <td>${p.gender || '-'}</td>
                    <td>${p.age || '-'}</td>
                    <td>${p.province || '-'}</td>
                    <td>${p.branch_id}</td>
                    <td>${p.enrolled_date || '-'}</td>
                </tr>`;
        });
    } catch (e) {
        console.error('participants error:', e);
    }
}


loadBranches();
loadBranchTable();
loadOrganizations();
initBranchSelector('branch-select', loadPending);
initBranchSelector('participant-branch-filter', loadParticipants);
loadParticipants();
