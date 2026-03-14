async function loadFeed() {
    try {
        const res = await fetch('/api/feed?limit=20');
        const data = await res.json();
        const list = document.getElementById('feed-list');
        list.innerHTML = '';

        data.forEach(item => {
            const time = item.timestamp ? new Date(item.timestamp).toLocaleString('th-TH') : '';
            list.innerHTML += `
                <div class="feed-item">
                    <div>${item.message}</div>
                    <div class="feed-time">${time}</div>
                </div>`;
        });
    } catch (e) {
        console.error('feed error:', e);
    }
}

loadFeed();
setInterval(loadFeed, 15000);
