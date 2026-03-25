/**
 * Branch Context — จำสาขาจาก URL param หรือ localStorage
 * ใช้ร่วมกันทุกหน้า (register, record, admin)
 *
 * Usage:
 *   const branchId = getBranchContext();
 *   setBranchContext('B001');
 *   initBranchSelector('select-id', onChangeCallback);
 */

const STORAGE_KEY = 'vidhisa_branch_id';

function getBranchContext() {
    const params = new URLSearchParams(window.location.search);
    const fromUrl = params.get('branch');
    if (fromUrl) {
        localStorage.setItem(STORAGE_KEY, fromUrl);
        return fromUrl;
    }
    return localStorage.getItem(STORAGE_KEY) || '';
}

function setBranchContext(branchId) {
    if (branchId) {
        localStorage.setItem(STORAGE_KEY, branchId);
    } else {
        localStorage.removeItem(STORAGE_KEY);
    }
    // Update URL without reload
    const url = new URL(window.location);
    if (branchId) {
        url.searchParams.set('branch', branchId);
    } else {
        url.searchParams.delete('branch');
    }
    window.history.replaceState({}, '', url);
}

async function initBranchSelector(selectId, onChange) {
    const sel = document.getElementById(selectId);
    if (!sel) return;

    const res = await fetch('/api/branches');
    const branches = await res.json();
    branches.forEach(b => {
        const opt = document.createElement('option');
        opt.value = b.id;
        opt.textContent = `${b.id} — ${b.name}`;
        sel.appendChild(opt);
    });

    const saved = getBranchContext();
    if (saved && sel.querySelector(`option[value="${saved}"]`)) {
        sel.value = saved;
    }

    sel.addEventListener('change', () => {
        setBranchContext(sel.value);
        if (onChange) onChange(sel.value);
    });

    // Trigger initial load if branch is set
    if (sel.value && onChange) onChange(sel.value);
}
