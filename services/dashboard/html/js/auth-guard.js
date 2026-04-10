/**
 * Auth Guard — เช็ค login ก่อนเข้าหน้า protected
 * ใส่ <script src="/js/auth-guard.js"></script> ในหน้าที่ต้อง login
 */

(function() {
    const token = localStorage.getItem('token');
    if (!token) {
        window.location.href = '/login.html';
        return;
    }

    // Verify token
    fetch('/api/auth/me', {headers: {'Authorization': `Bearer ${token}`}})
        .then(r => {
            if (!r.ok) throw 'expired';
            return r.json();
        })
        .then(user => {
            window._currentUser = user;
            // Dispatch event for pages to use
            window.dispatchEvent(new CustomEvent('auth-ready', {detail: user}));
        })
        .catch(() => {
            localStorage.removeItem('token');
            localStorage.removeItem('user');
            document.cookie = 'token=; path=/; max-age=0';
            window.location.href = '/login.html';
        });
})();

function getToken() {
    return localStorage.getItem('token');
}

function getCurrentUser() {
    return window._currentUser || JSON.parse(localStorage.getItem('user') || '{}');
}

function logout() {
    localStorage.removeItem('token');
    localStorage.removeItem('user');
    document.cookie = 'token=; path=/; max-age=0';
    window.location.href = '/login.html';
}

function authFetch(url, options = {}) {
    const token = getToken();
    if (!options.headers) options.headers = {};
    if (token) options.headers['Authorization'] = `Bearer ${token}`;
    return fetch(url, options);
}
