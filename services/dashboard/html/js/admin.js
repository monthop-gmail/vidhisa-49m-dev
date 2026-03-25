const FMT = new Intl.NumberFormat('th-TH');
let branchMode = false; // true = admin สาขา, false = admin กลาง

async function loadBranches() {
    // kept for branch table
}

async function loadPending() {
    const branchId = branchMode ? getBranchContext() : document.getElementById('branch-select').value;
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
        let data = await res.json();
        if (branchMode) {
            const bid = getBranchContext();
            data = data.filter(o => o.branch_id === bid);
        }
        const tbody = document.querySelector('#org-table tbody');
        tbody.innerHTML = '';
        data.forEach(o => {
            tbody.innerHTML += `
                <tr>
                    <td>${o.id}</td>
                    <td>${o.name}</td>
                    <td>${o.org_type || '-'}</td>
                    <td>${o.province || '-'}</td>
                    <td>${o.branch_id || '-'}</td>
                    <td>${FMT.format(o.total_minutes)}</td>
                    <td>${FMT.format(o.total_records)}</td>
                </tr>`;
        });
    } catch (e) {
        console.error('org error:', e);
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
        const branchId = branchMode ? getBranchContext() : '';
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


// Detect branch mode
const contextBranch = getBranchContext();
branchMode = !!contextBranch;

// Init branch selector (no auto-redirect on init)
async function initAdmin() {
    const res = await fetch('/api/branches');
    const branches = await res.json();
    const sel = document.getElementById('branch-select');
    branches.forEach(b => {
        const opt = document.createElement('option');
        opt.value = b.id;
        opt.textContent = `${b.id} — ${b.name}`;
        sel.appendChild(opt);
    });

    // Set saved value without triggering change
    if (contextBranch && sel.querySelector(`option[value="${contextBranch}"]`)) {
        sel.value = contextBranch;
    }

    // On change → navigate
    sel.addEventListener('change', () => {
        const bid = sel.value;
        setBranchContext(bid);
        if (bid) {
            window.location.href = `/admin.html?branch=${bid}`;
        } else {
            window.location.href = '/admin.html';
        }
    });

    // Apply mode
    if (branchMode) {
        document.getElementById('admin-title').textContent = `Admin สาขา ${contextBranch}`;
        document.getElementById('section-branches').style.display = 'none';
        document.getElementById('org-section-title').textContent = `องค์กรในสาขา ${contextBranch}`;

        const orgBranchSel = document.getElementById('org-branch');
        if (orgBranchSel) {
            orgBranchSel.innerHTML = `<option value="${contextBranch}" selected>${contextBranch}</option>`;
            orgBranchSel.disabled = true;
        }

        loadPending();
        loadOrganizations();
        loadParticipants();
        loadBulkRecords();
        loadIndRecords();
        updateLinks();
    } else {
        document.getElementById('admin-title').textContent = 'Admin กลาง';
        loadBranches();
        loadBranchTable();
        loadOrganizations();
        loadParticipants();
        loadBulkRecords();
        loadIndRecords();
        updateLinks();
    }
}

async function loadBulkRecords() {
    try {
        const bid = branchMode ? getBranchContext() : '';
        const url = bid ? `/api/records?record_type=bulk&branch_id=${bid}` : '/api/records?record_type=bulk';
        const res = await fetch(url);
        const data = await res.json();
        const tbody = document.querySelector('#bulk-record-table tbody');
        const empty = document.getElementById('bulk-record-empty');
        const count = document.getElementById('bulk-record-count');
        tbody.innerHTML = '';
        count.textContent = `(${data.length} รายการ)`;
        if (data.length === 0) { empty.style.display = 'block'; return; }
        empty.style.display = 'none';
        data.forEach(r => {
            const chk = v => v ? '✓' : '';
            tbody.innerHTML += `<tr>
                <td>${r.id}</td><td>${r.name}</td><td>${FMT.format(r.minutes)}</td>
                <td>${r.participant_count || '-'}</td>
                <td>${chk(r.session_morning)}</td><td>${chk(r.session_afternoon)}</td><td>${chk(r.session_evening)}</td>
                <td>${r.date}</td><td>${r.status}</td></tr>`;
        });
    } catch (e) { console.error('bulk records error:', e); }
}

async function loadIndRecords() {
    try {
        const bid = branchMode ? getBranchContext() : '';
        const url = bid ? `/api/records?record_type=individual&branch_id=${bid}` : '/api/records?record_type=individual';
        const res = await fetch(url);
        const data = await res.json();
        const tbody = document.querySelector('#ind-record-table tbody');
        const empty = document.getElementById('ind-record-empty');
        const count = document.getElementById('ind-record-count');
        tbody.innerHTML = '';
        count.textContent = `(${data.length} รายการ)`;
        if (data.length === 0) { empty.style.display = 'block'; return; }
        empty.style.display = 'none';
        data.forEach(r => {
            const chk = v => v ? '✓' : '';
            tbody.innerHTML += `<tr>
                <td>${r.id}</td><td>${r.name}</td><td>${FMT.format(r.minutes)}</td>
                <td>${chk(r.session_morning)}</td><td>${chk(r.session_afternoon)}</td><td>${chk(r.session_evening)}</td>
                <td>${r.date}</td><td>${r.status}</td></tr>`;
        });
    } catch (e) { console.error('ind records error:', e); }
}

async function importParticipants(input) {
    const file = input.files[0];
    if (!file) return;

    const status = document.getElementById('import-participant-status');
    status.textContent = 'กำลังนำเข้า...';
    status.style.color = '#666';

    try {
        const formData = new FormData();
        formData.append('file', file);
        const res = await fetch('/api/participants/import', { method: 'POST', body: formData });
        const data = await res.json();
        if (res.ok) {
            status.textContent = data.message;
            status.style.color = '#43a047';
            if (data.errors.length > 0) {
                status.textContent += ' | ' + data.errors.join(', ');
                status.style.color = '#e65100';
            }
            loadParticipants();
        } else {
            status.textContent = data.detail?.message || 'เกิดข้อผิดพลาด';
            status.style.color = '#e53935';
        }
    } catch (e) {
        console.error('import participants error:', e);
        status.textContent = 'เกิดข้อผิดพลาด';
        status.style.color = '#e53935';
    }
    input.value = '';
}

function updateLinks() {
    const bid = branchMode ? getBranchContext() : '';

    const exportLink = document.getElementById('export-participant-link');
    if (exportLink) exportLink.href = bid ? `/api/participants/export?branch_id=${bid}` : '/api/participants/export';

    const addOrgLink = document.getElementById('add-org-link');
    if (addOrgLink) addOrgLink.href = bid ? `/register.html?branch=${bid}` : '/register.html';

    const addPLink = document.getElementById('add-participant-link');
    if (addPLink) addPLink.href = bid ? `/register.html?branch=${bid}#individual` : '/register.html#individual';

    const addBulkLink = document.getElementById('add-bulk-link');
    if (addBulkLink) addBulkLink.href = bid ? `/record.html?branch=${bid}` : '/record.html';

    const addIndLink = document.getElementById('add-ind-link');
    if (addIndLink) addIndLink.href = bid ? `/record.html?branch=${bid}#ind` : '/record.html#ind';

    const exportBulk = document.getElementById('export-bulk-link');
    if (exportBulk) exportBulk.href = bid ? `/api/records/export?record_type=bulk&branch_id=${bid}` : '/api/records/export?record_type=bulk';

    const exportInd = document.getElementById('export-ind-link');
    if (exportInd) exportInd.href = bid ? `/api/records/export?record_type=individual&branch_id=${bid}` : '/api/records/export?record_type=individual';
}

initAdmin();
