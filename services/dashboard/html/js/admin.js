const FMT = new Intl.NumberFormat('th-TH');
const PAGE_SIZE = 50;
let branchMode = false;

// Pagination state
let participantOffset = 0;
let bulkRecordOffset = 0;
let indRecordOffset = 0;

// === Toggle checkbox ===
function toggleCb(headerCb, cbClass) {
    document.querySelectorAll('.' + cbClass).forEach(c => c.checked = headerCb.checked);
}

function getCheckedIds(cbClass) {
    return [...document.querySelectorAll('.' + cbClass + ':checked')].map(c => c.value);
}

// === Pending Organizations ===
async function loadPendingOrgs() {
    try {
        const res = await fetch('/api/organizations');
        let data = await res.json();
        data = data.filter(o => o.status === 'pending' || !o.status);
        if (branchMode) data = data.filter(o => o.branch_id === getBranchContext());
        const tbody = document.querySelector('#pending-org-table tbody');
        const empty = document.getElementById('pending-org-empty');
        const count = document.getElementById('pending-org-count');
        const btn = document.getElementById('btn-approve-org');
        tbody.innerHTML = '';
        count.textContent = `(${data.length})`;
        if (data.length === 0) { empty.style.display = 'block'; if (btn) btn.style.display = 'none'; return; }
        empty.style.display = 'none';
        if (btn) btn.style.display = 'inline-block';
        data.forEach(o => {
            tbody.innerHTML += `<tr>
                <td><input type="checkbox" class="pending-org-cb" value="${o.id}"></td>
                <td>${o.id}</td><td>${o.name}</td><td>${o.org_type || '-'}</td><td>${o.branch_id || '-'}</td>
                <td><button class="btn-approve" onclick="approveOne('org','${o.id}')">อนุมัติ</button>
                <button class="btn-reject" onclick="rejectOne('org','${o.id}')">ปฏิเสธ</button></td></tr>`;
        });
    } catch (e) { console.error('pending org error:', e); }
}

// === Pending Participants ===
async function loadPendingParticipants() {
    try {
        const bid = branchMode ? getBranchContext() : '';
        const url = bid ? `/api/participants?branch_id=${bid}&limit=200` : '/api/participants?limit=200';
        const res = await fetch(url);
        let data = await res.json();
        data = data.filter(p => p.status === 'pending' || !p.status);
        const tbody = document.querySelector('#pending-p-table tbody');
        const empty = document.getElementById('pending-p-empty');
        const count = document.getElementById('pending-p-count');
        const btn = document.getElementById('btn-approve-p');
        tbody.innerHTML = '';
        count.textContent = `(${data.length})`;
        if (data.length === 0) { empty.style.display = 'block'; if (btn) btn.style.display = 'none'; return; }
        empty.style.display = 'none';
        if (btn) btn.style.display = 'inline-block';
        data.forEach(p => {
            tbody.innerHTML += `<tr>
                <td><input type="checkbox" class="pending-p-cb" value="${p.id}"></td>
                <td>${p.id}</td><td>${p.first_name}</td><td>${p.last_name}</td><td>${p.branch_id}</td>
                <td><button class="btn-approve" onclick="approveOne('participant',${p.id})">อนุมัติ</button>
                <button class="btn-reject" onclick="rejectOne('participant',${p.id})">ปฏิเสธ</button></td></tr>`;
        });
    } catch (e) { console.error('pending participant error:', e); }
}

// === Pending Records ===
async function loadPending() {
    const branchId = branchMode ? getBranchContext() : document.getElementById('branch-select').value;
    if (!branchId) return;

    try {
        const res = await fetch(`/api/branch/${branchId}/pending`);
        const data = await res.json();
        const tbody = document.querySelector('#pending-table tbody');
        const empty = document.getElementById('pending-empty');
        const count = document.getElementById('pending-count');
        const btn = document.getElementById('btn-approve-all');
        tbody.innerHTML = '';
        count.textContent = `(${data.length})`;
        if (data.length === 0) { empty.style.display = 'block'; if (btn) btn.style.display = 'none'; return; }
        empty.style.display = 'none';
        if (btn) btn.style.display = 'inline-block';
        data.forEach(r => {
            const flags = (r.flags || []).map(f => `<span class="flag-badge">${f}</span>`).join(' ');
            tbody.innerHTML += `<tr>
                <td><input type="checkbox" class="pending-rec-cb" value="${r.id}"></td>
                <td>${r.id}</td><td>${r.type}</td><td>${r.name}</td><td>${r.minutes}</td>
                <td>${r.date}</td><td>${flags}</td>
                <td><button class="btn-approve" onclick="approveOne('record',${r.id})">อนุมัติ</button>
                <button class="btn-reject" onclick="rejectOne('record',${r.id})">ปฏิเสธ</button></td></tr>`;
        });
    } catch (e) { console.error('pending error:', e); }
}

// === Approve / Reject single ===
const API_MAP = {
    org: { approve: id => `/api/organizations/${id}/approve`, reject: id => `/api/organizations/${id}/reject` },
    participant: { approve: id => `/api/participants/${id}/approve`, reject: id => `/api/participants/${id}/reject` },
    record: { approve: id => `/api/records/${id}/approve`, reject: id => `/api/records/${id}/reject` },
};

async function approveOne(type, id) {
    const body = type === 'record' ? JSON.stringify({approved_by: 'สาขา Admin'}) : '{}';
    await fetch(API_MAP[type].approve(id), { method: 'PATCH', headers: {'Content-Type': 'application/json'}, body });
    refreshPending();
}

async function rejectOne(type, id) {
    const reason = type === 'record' ? prompt('เหตุผลที่ปฏิเสธ:') : prompt('เหตุผล:');
    if (reason === null) return;
    const body = type === 'record' ? JSON.stringify({reason}) : '{}';
    await fetch(API_MAP[type].reject(id), { method: 'PATCH', headers: {'Content-Type': 'application/json'}, body });
    refreshPending();
}

// === Approve selected batch ===
async function approveAllType(type) {
    const cbClass = type === 'org' ? 'pending-org-cb' : type === 'participant' ? 'pending-p-cb' : 'pending-rec-cb';
    const ids = getCheckedIds(cbClass);
    if (ids.length === 0) { alert('กรุณาเลือกรายการ'); return; }
    if (!confirm(`อนุมัติ ${ids.length} รายการ?`)) return;

    let success = 0;
    for (const id of ids) {
        try {
            const body = type === 'record' ? JSON.stringify({approved_by: 'สาขา Admin'}) : '{}';
            const res = await fetch(API_MAP[type].approve(id), { method: 'PATCH', headers: {'Content-Type': 'application/json'}, body });
            if (res.ok) success++;
        } catch (e) { console.error(`approve ${type} ${id} error:`, e); }
    }
    alert(`อนุมัติสำเร็จ ${success}/${ids.length}`);
    refreshPending();
}

function refreshPending() {
    loadPendingOrgs();
    loadPendingParticipants();
    loadPending();
}

// approve/reject ใช้ approveOne/rejectOne แทน

async function loadOrganizations() {
    try {
        const res = await fetch('/api/organizations');
        let data = await res.json();
        if (branchMode) {
            data = data.filter(o => o.branch_id === getBranchContext());
        }
        const tbody = document.querySelector('#org-table tbody');
        tbody.innerHTML = '';
        data.forEach(o => {
            tbody.innerHTML += `<tr>
                <td>${o.id}</td><td>${o.name}</td><td>${o.org_type || '-'}</td>
                <td>${o.province || '-'}</td><td>${o.branch_id || '-'}</td>
                <td>${o.status || '-'}</td>
                <td>${FMT.format(o.total_minutes)}</td><td>${FMT.format(o.total_records)}</td></tr>`;
        });
    } catch (e) { console.error('org error:', e); }
}

async function loadBranchTable() {
    try {
        const res = await fetch('/api/branches');
        const data = await res.json();
        const tbody = document.querySelector('#branch-table tbody');
        tbody.innerHTML = '';
        data.forEach(b => {
            tbody.innerHTML += `<tr>
                <td>${b.id}</td><td>${b.name}</td><td>${b.group_id || '-'}</td>
                <td>${b.province}</td><td>${b.admin_name || '-'}</td>
                <td>${FMT.format(b.total_minutes)}</td><td>${FMT.format(b.total_records)}</td></tr>`;
        });
    } catch (e) { console.error('branch table error:', e); }
}

async function loadParticipants(append) {
    try {
        if (!append) participantOffset = 0;
        const branchId = branchMode ? getBranchContext() : '';
        const url = branchId
            ? `/api/participants?branch_id=${branchId}&limit=${PAGE_SIZE}&offset=${participantOffset}`
            : `/api/participants?limit=${PAGE_SIZE}&offset=${participantOffset}`;
        const res = await fetch(url);
        const data = await res.json();
        const tbody = document.querySelector('#participant-table tbody');
        const empty = document.getElementById('participant-empty');
        const count = document.getElementById('participant-count');
        const moreBtn = document.getElementById('participant-more');

        if (!append) tbody.innerHTML = '';
        count.textContent = '';

        if (data.length === 0 && participantOffset === 0) {
            empty.style.display = 'block';
            if (moreBtn) moreBtn.style.display = 'none';
            return;
        }
        empty.style.display = 'none';

        data.forEach(p => {
            tbody.innerHTML += `<tr>
                <td>${p.id}</td><td>${p.prefix || '-'}</td><td>${p.first_name}</td>
                <td>${p.last_name}</td><td>${p.gender || '-'}</td><td>${p.age || '-'}</td>
                <td>${p.province || '-'}</td><td>${p.branch_id}</td><td>${p.status || '-'}</td><td>${p.enrolled_date || '-'}</td></tr>`;
        });

        participantOffset += data.length;
        if (moreBtn) moreBtn.style.display = data.length >= PAGE_SIZE ? 'inline-block' : 'none';
    } catch (e) { console.error('participants error:', e); }
}

async function loadBulkRecords(append) {
    try {
        if (!append) bulkRecordOffset = 0;
        const bid = branchMode ? getBranchContext() : '';
        const url = bid
            ? `/api/records?record_type=bulk&branch_id=${bid}&limit=${PAGE_SIZE}&offset=${bulkRecordOffset}`
            : `/api/records?record_type=bulk&limit=${PAGE_SIZE}&offset=${bulkRecordOffset}`;
        const res = await fetch(url);
        const data = await res.json();
        const tbody = document.querySelector('#bulk-record-table tbody');
        const empty = document.getElementById('bulk-record-empty');
        const count = document.getElementById('bulk-record-count');
        const moreBtn = document.getElementById('bulk-record-more');

        if (!append) tbody.innerHTML = '';
        count.textContent = '';

        if (data.length === 0 && bulkRecordOffset === 0) { empty.style.display = 'block'; if (moreBtn) moreBtn.style.display = 'none'; return; }
        empty.style.display = 'none';

        data.forEach(r => {
            const ms = (r.morning_male||0)+(r.morning_female||0)+(r.morning_unspecified||0);
            const as = (r.afternoon_male||0)+(r.afternoon_female||0)+(r.afternoon_unspecified||0);
            const es = (r.evening_male||0)+(r.evening_female||0)+(r.evening_unspecified||0);
            tbody.innerHTML += `<tr>
                <td>${r.id}</td><td>${r.name}</td><td>${FMT.format(r.minutes)}</td>
                <td>${ms || '-'}</td><td>${as || '-'}</td><td>${es || '-'}</td>
                <td>${r.date}</td><td>${r.status}</td></tr>`;
        });

        bulkRecordOffset += data.length;
        if (moreBtn) moreBtn.style.display = data.length >= PAGE_SIZE ? 'inline-block' : 'none';
    } catch (e) { console.error('bulk records error:', e); }
}

async function loadIndRecords(append) {
    try {
        if (!append) indRecordOffset = 0;
        const bid = branchMode ? getBranchContext() : '';
        const url = bid
            ? `/api/records?record_type=individual&branch_id=${bid}&limit=${PAGE_SIZE}&offset=${indRecordOffset}`
            : `/api/records?record_type=individual&limit=${PAGE_SIZE}&offset=${indRecordOffset}`;
        const res = await fetch(url);
        const data = await res.json();
        const tbody = document.querySelector('#ind-record-table tbody');
        const empty = document.getElementById('ind-record-empty');
        const count = document.getElementById('ind-record-count');
        const moreBtn = document.getElementById('ind-record-more');

        if (!append) tbody.innerHTML = '';
        count.textContent = '';

        if (data.length === 0 && indRecordOffset === 0) { empty.style.display = 'block'; if (moreBtn) moreBtn.style.display = 'none'; return; }
        empty.style.display = 'none';

        data.forEach(r => {
            const ms = (r.morning_male||0)+(r.morning_female||0)+(r.morning_unspecified||0);
            const as = (r.afternoon_male||0)+(r.afternoon_female||0)+(r.afternoon_unspecified||0);
            const es = (r.evening_male||0)+(r.evening_female||0)+(r.evening_unspecified||0);
            tbody.innerHTML += `<tr>
                <td>${r.id}</td><td>${r.name}</td><td>${FMT.format(r.minutes)}</td>
                <td>${ms ? '✓' : ''}</td><td>${as ? '✓' : ''}</td><td>${es ? '✓' : ''}</td>
                <td>${r.date}</td><td>${r.status}</td></tr>`;
        });

        indRecordOffset += data.length;
        if (moreBtn) moreBtn.style.display = data.length >= PAGE_SIZE ? 'inline-block' : 'none';
    } catch (e) { console.error('ind records error:', e); }
}

async function importBranches(input) {
    const file = input.files[0]; if (!file) return;
    const status = document.getElementById('import-branch-status');
    status.textContent = 'กำลังนำเข้า...'; status.style.color = '#666';
    try {
        const fd = new FormData(); fd.append('file', file);
        const res = await fetch('/api/branches/import', { method: 'POST', body: fd });
        const data = await res.json();
        if (res.ok) { status.textContent = data.message; status.style.color = '#43a047'; loadBranchTable(); }
        else { status.textContent = data.detail?.message || 'เกิดข้อผิดพลาด'; status.style.color = '#e53935'; }
    } catch (e) { status.textContent = 'เกิดข้อผิดพลาด'; status.style.color = '#e53935'; }
    input.value = '';
}

async function importOrgs(input) {
    const file = input.files[0]; if (!file) return;
    const status = document.getElementById('import-status');
    status.textContent = 'กำลังนำเข้า...'; status.style.color = '#666';
    try {
        const fd = new FormData(); fd.append('file', file);
        const res = await fetch('/api/organizations/import', { method: 'POST', body: fd });
        const data = await res.json();
        if (res.ok) { status.textContent = data.message; status.style.color = '#43a047'; loadOrganizations(); }
        else { status.textContent = data.detail?.message || 'เกิดข้อผิดพลาด'; status.style.color = '#e53935'; }
    } catch (e) { status.textContent = 'เกิดข้อผิดพลาด'; status.style.color = '#e53935'; }
    input.value = '';
}

async function importRecords(input, type) {
    const file = input.files[0]; if (!file) return;
    const statusId = type === 'bulk' ? 'import-bulk-status' : 'import-ind-status';
    const status = document.getElementById(statusId);
    status.textContent = 'กำลังนำเข้า...'; status.style.color = '#666';
    try {
        const fd = new FormData(); fd.append('file', file);
        const res = await fetch('/api/records/import', { method: 'POST', body: fd });
        const data = await res.json();
        if (res.ok) { status.textContent = data.message; status.style.color = '#43a047'; loadBulkRecords(); loadIndRecords(); }
        else { status.textContent = data.detail?.message || 'เกิดข้อผิดพลาด'; status.style.color = '#e53935'; }
    } catch (e) { status.textContent = 'เกิดข้อผิดพลาด'; status.style.color = '#e53935'; }
    input.value = '';
}

async function importParticipants(input) {
    const file = input.files[0]; if (!file) return;
    const status = document.getElementById('import-participant-status');
    status.textContent = 'กำลังนำเข้า...'; status.style.color = '#666';
    try {
        const fd = new FormData(); fd.append('file', file);
        const res = await fetch('/api/participants/import', { method: 'POST', body: fd });
        const data = await res.json();
        if (res.ok) { status.textContent = data.message; status.style.color = '#43a047'; loadParticipants(); }
        else { status.textContent = data.detail?.message || 'เกิดข้อผิดพลาด'; status.style.color = '#e53935'; }
    } catch (e) { status.textContent = 'เกิดข้อผิดพลาด'; status.style.color = '#e53935'; }
    input.value = '';
}

function updateLinks() {
    const bid = branchMode ? getBranchContext() : '';
    const el = (id) => document.getElementById(id);

    if (el('export-participant-link')) el('export-participant-link').href = bid ? `/api/participants/export?branch_id=${bid}` : '/api/participants/export';
    if (el('add-org-link')) el('add-org-link').href = bid ? `/register.html?branch=${bid}` : '/register.html';
    if (el('add-participant-link')) el('add-participant-link').href = bid ? `/register.html?branch=${bid}#individual` : '/register.html#individual';
    if (el('add-bulk-link')) el('add-bulk-link').href = bid ? `/record.html?branch=${bid}` : '/record.html';
    if (el('add-ind-link')) el('add-ind-link').href = bid ? `/record.html?branch=${bid}#ind` : '/record.html#ind';
    if (el('export-bulk-link')) el('export-bulk-link').href = bid ? `/api/records/export?record_type=bulk&branch_id=${bid}` : '/api/records/export?record_type=bulk';
    if (el('export-ind-link')) el('export-ind-link').href = bid ? `/api/records/export?record_type=individual&branch_id=${bid}` : '/api/records/export?record_type=individual';
}

function showSummaryMessage(sectionId, message) {
    const tbody = document.querySelector(`#${sectionId} tbody`);
    if (tbody) tbody.innerHTML = `<tr><td colspan="10" style="text-align:center; color:#999; padding:1rem;">${message}</td></tr>`;
}

// === Enrollments (central admin only) ===
async function loadEnrollments() {
    try {
        const res = await authFetch('/api/enrollments');
        if (!res.ok) return;
        const data = await res.json();
        const tbody = document.querySelector('#enrollment-table tbody');
        const empty = document.getElementById('enrollment-empty');
        const count = document.getElementById('enrollment-count');
        tbody.innerHTML = '';
        count.textContent = `(${data.length} สาขา, pending ${data.filter(e => e.status === 'pending').length})`;

        if (data.length === 0) { empty.style.display = 'block'; return; }
        empty.style.display = 'none';

        data.forEach(e => {
            const statusColor = e.status === 'approved' ? '#43a047' : e.status === 'rejected' ? '#e53935' : '#e65100';
            let actions = '';
            if (e.status === 'pending') {
                actions = `<button class="btn-approve" onclick="approveEnrollment(${e.id})">อนุมัติ</button> <button class="btn-reject" onclick="rejectEnrollment(${e.id})">ปฏิเสธ</button>`;
            } else {
                actions = `<span style="color:${statusColor}">${e.status}</span>`;
            }
            actions += ` <button style="font-size:0.75rem; padding:0.1rem 0.4rem; cursor:pointer;" onclick="editBranchNum(${e.id}, '${e.branch_number || ''}')">แก้เลข</button>`;
            tbody.innerHTML += `<tr>
                <td>${e.id}</td><td>${e.branch_number || '-'}</td><td>${e.branch_name}</td>
                <td>${e.admin1_name || '-'}<br><small>${e.admin1_email || ''}</small></td>
                <td>${e.admin2_name || '-'}<br><small>${e.admin2_email || ''}</small></td>
                <td>${e.admin3_name || '-'}<br><small>${e.admin3_email || ''}</small></td>
                <td style="color:${statusColor}">${e.status}</td>
                <td>${actions}</td></tr>`;
        });
    } catch (e) { console.error('enrollments error:', e); }
}

async function syncEnrollments() {
    const status = document.getElementById('sync-status');
    status.textContent = 'กำลังดึงข้อมูล...';
    status.style.color = '#666';
    try {
        const res = await authFetch('/api/enrollments/sync', { method: 'POST' });
        const data = await res.json();
        if (res.ok) {
            status.textContent = data.message;
            status.style.color = '#43a047';
            loadEnrollments();
        } else {
            status.textContent = data.detail?.message || 'เกิดข้อผิดพลาด';
            status.style.color = '#e53935';
        }
    } catch (e) {
        status.textContent = 'เกิดข้อผิดพลาด';
        status.style.color = '#e53935';
    }
}

async function approveEnrollment(id) {
    if (!confirm('อนุมัติสาขานี้? ระบบจะสร้าง user/password ให้ admin สาขา')) return;
    const res = await authFetch(`/api/enrollments/${id}/approve`, { method: 'PATCH' });
    const data = await res.json();
    if (res.ok) {
        let msg = data.message;
        if (data._credentials && data._credentials.length > 0) {
            msg += '\n\nUser/Password ที่สร้าง:\n';
            data._credentials.forEach(c => { msg += `${c.username} / ${c.password} (${c.name})\n`; });
        }
        alert(msg);
        loadEnrollments();
        loadUsers();
    } else {
        alert(data.detail?.message || 'เกิดข้อผิดพลาด');
    }
}

async function editBranchNum(id, current) {
    const num = prompt(`แก้เลขสาขา (ปัจจุบัน: ${current || 'ว่าง'}):`, current || '');
    if (num === null) return;
    const res = await authFetch(`/api/enrollments/${id}/update-branch`, {
        method: 'PATCH', headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({branch_number: num}),
    });
    const data = await res.json();
    if (res.ok) { alert(data.message); loadEnrollments(); loadUsers(); }
    else alert(data.detail?.message || 'เกิดข้อผิดพลาด');
}

async function rejectEnrollment(id) {
    if (!confirm('ปฏิเสธสาขานี้?')) return;
    await authFetch(`/api/enrollments/${id}/reject`, { method: 'PATCH' });
    loadEnrollments();
}

// === Users (central admin only) ===
async function loadUsers() {
    try {
        const res = await authFetch('/api/users');
        if (!res.ok) return;
        const data = await res.json();
        const tbody = document.querySelector('#user-table tbody');
        const count = document.getElementById('user-count');
        tbody.innerHTML = '';
        count.textContent = `(${data.length} คน)`;

        data.forEach(u => {
            const editBtn = u.role === 'branch_admin'
                ? `<button style="font-size:0.75rem; padding:0.1rem 0.4rem; cursor:pointer;" onclick="editUser(${u.id}, '${u.username}', '${u.email || ''}')">แก้ไข</button>`
                : '';
            tbody.innerHTML += `<tr>
                <td>${u.id}</td><td>${u.username}</td><td>${u.full_name}</td>
                <td>${u.email || '-'}</td><td>${u.role}</td>
                <td>${u.branch_id || '-'}</td><td>${u.status}</td><td>${editBtn}</td></tr>`;
        });
    } catch (e) { console.error('users error:', e); }
}

// === GGS Sync (branch admin) ===
async function loadGgsUrl() {
    const bid = getBranchContext();
    if (!bid) return;
    try {
        const res = await fetch('/api/ggs/sources');
        const data = await res.json();
        const branch = data.find(b => b.branch_id === bid);
        if (branch && branch.ggs_url) {
            document.getElementById('ggs-url-input').value = branch.ggs_url;
        }
    } catch (e) { console.error('load ggs url error:', e); }
}

async function saveGgsUrl() {
    const url = document.getElementById('ggs-url-input').value.trim();
    const bid = getBranchContext();
    const status = document.getElementById('ggs-sync-status');
    const res = await authFetch('/api/ggs/set-url', {
        method: 'PATCH', headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({branch_id: bid, url: url}),
    });
    const data = await res.json();
    if (res.ok) { status.textContent = data.message; status.style.color = '#43a047'; }
    else { status.textContent = data.detail?.message || 'เกิดข้อผิดพลาด'; status.style.color = '#e53935'; }
}

async function syncBranchGgs() {
    const bid = getBranchContext();
    const status = document.getElementById('ggs-sync-status');
    status.textContent = 'กำลังดึงข้อมูล...'; status.style.color = '#666';
    try {
        const res = await authFetch('/api/ggs/sync-branch', {
            method: 'POST', headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({branch_id: bid}),
        });
        const data = await res.json();
        if (res.ok) {
            let msg = `สำเร็จ:`;
            if (data.organizations) msg += ` org +${data.organizations.created || 0}`;
            if (data.participants) msg += ` | participants +${data.participants.created || 0}`;
            if (data.records) msg += ` | records +${data.records.created || 0}`;
            status.textContent = msg; status.style.color = '#43a047';
            // Refresh tables
            loadPendingOrgs(); loadPendingParticipants(); loadPending();
            loadOrganizations(); loadParticipants();
            loadBulkRecords(); loadIndRecords();
        } else {
            status.textContent = data.detail?.message || 'เกิดข้อผิดพลาด'; status.style.color = '#e53935';
        }
    } catch (e) { status.textContent = 'เกิดข้อผิดพลาด'; status.style.color = '#e53935'; }
}

async function editUser(id, currentUsername, currentEmail) {
    const newUsername = prompt(`แก้ username (ปัจจุบัน: ${currentUsername})\nแนะนำใช้ email:`, currentEmail || currentUsername);
    if (newUsername === null) return;
    const res = await authFetch(`/api/users/${id}`, {
        method: 'PATCH', headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({username: newUsername}),
    });
    const data = await res.json();
    if (res.ok) { alert(data.message); loadUsers(); }
    else alert(data.detail?.message || 'เกิดข้อผิดพลาด');
}

// Detect branch mode
const contextBranch = getBranchContext();
branchMode = !!contextBranch;

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

    if (contextBranch && sel.querySelector(`option[value="${contextBranch}"]`)) {
        sel.value = contextBranch;
    }

    sel.addEventListener('change', () => {
        const bid = sel.value;
        setBranchContext(bid);
        if (bid) window.location.href = `/admin.html?branch=${bid}`;
        else window.location.href = '/admin.html';
    });

    if (branchMode) {
        // Admin สาขา — โหลดข้อมูลเฉพาะสาขา + pagination
        document.getElementById('admin-title').textContent = `Admin สาขา ${contextBranch}`;
        document.getElementById('section-branches').style.display = 'none';
        document.getElementById('org-section-title').textContent = `องค์กรในสาขา ${contextBranch}`;

        document.getElementById('section-ggs-sync').style.display = 'block';
        loadGgsUrl();
        loadPendingOrgs();
        loadPendingParticipants();
        loadPending();
        loadOrganizations();
        loadParticipants();
        loadBulkRecords();
        loadIndRecords();
    } else {
        // Admin กลาง — แสดงสรุป ไม่โหลดข้อมูลหนัก
        document.getElementById('admin-title').textContent = 'Admin กลาง';
        document.getElementById('section-enrollments').style.display = 'block';
        document.getElementById('section-users').style.display = 'block';
        loadEnrollments();
        loadUsers();
        loadPendingOrgs();
        loadPendingParticipants();
        loadBranchTable();
        loadOrganizations();

        // ไม่โหลด participants/records ทั้งหมด — แสดงข้อความแทน
        showSummaryMessage('participant-table', 'เลือกสาขาด้านบนเพื่อดูรายชื่อ');
        showSummaryMessage('bulk-record-table', 'เลือกสาขาด้านบนเพื่อดูบันทึก');
        showSummaryMessage('ind-record-table', 'เลือกสาขาด้านบนเพื่อดูบันทึก');
    }

    // Show username
    const user = getCurrentUser();
    const ud = document.getElementById('user-display');
    if (ud && user.full_name) ud.textContent = `${user.full_name} (${user.role})`;

    updateLinks();
}

initAdmin();
