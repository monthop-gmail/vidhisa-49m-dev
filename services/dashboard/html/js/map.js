let map, geoLayer;
let provinceData = {};
let provinceTotal = 0;
let groupData = [];
let markerLayer = null;
let currentView = 'province';
const FMT_MAP = new Intl.NumberFormat('th-TH');

function initMap() {
    map = L.map('map').setView([13.0, 101.0], 5);
    L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
        attribution: '&copy; OpenStreetMap',
        maxZoom: 18,
    }).addTo(map);

    loadProvinceData();
}

async function loadProvinceData() {
    try {
        const [statsRes, geoRes] = await Promise.all([
            fetch('/api/stats/by-province'),
            fetch('/data/thailand.geojson'),
        ]);
        const stats = await statsRes.json();
        const geo = await geoRes.json();

        stats.forEach(s => { provinceData[s.code] = s; });
        provinceTotal = stats.reduce((sum, s) => sum + (s.minutes || 0), 0);

        geoLayer = L.geoJSON(geo, {
            style: feature => getProvinceStyle(feature),
            onEachFeature: (feature, layer) => {
                layer.on('mouseover', function (e) {
                    const code = getProvinceCode(feature);
                    const data = provinceData[code];
                    const name = feature.properties.NAME_1 || feature.properties.name || code;
                    const rawMin = data ? data.minutes : 0;
                    const minutes = FMT_MAP.format(rawMin);
                    const pctStr = provinceTotal > 0 ? ` (${(rawMin/provinceTotal*100).toFixed(2)}%)` : '';
                    layer.bindTooltip(`${name}<br>${minutes} นาที${pctStr}`).openTooltip();
                    layer.setStyle({ weight: 3, fillOpacity: 0.8 });
                });
                layer.on('mouseout', function () {
                    geoLayer.resetStyle(layer);
                });
            }
        }).addTo(map);

        // Also load group data
        const groupRes = await fetch('/api/stats/by-group');
        groupData = await groupRes.json();
    } catch (e) {
        console.error('map error:', e);
    }
}

function getProvinceCode(feature) {
    const name = feature.properties.name || feature.properties.NAME_1 || '';
    return PROVINCE_CODE_MAP[name] || '';
}

function getProvinceStyle(feature) {
    const code = getProvinceCode(feature);

    if (currentView === 'markers') {
        return { fillColor: '#f0f0f0', weight: 1, color: '#ccc', fillOpacity: 0.3 };
    }

    if (currentView === 'province') {
        const data = provinceData[code];
        const minutes = data ? data.minutes : 0;
        return {
            fillColor: getColor(minutes),
            weight: 1,
            color: '#999',
            fillOpacity: 0.6,
        };
    } else {
        // Group view
        const colors = ['#1b9e77','#d95f02','#7570b3','#e7298a','#66a61e','#e6ab02','#a6761d','#666666','#e41a1c','#377eb8'];
        let groupIdx = -1;
        for (let i = 0; i < groupData.length; i++) {
            if (groupData[i].province_codes.includes(code)) {
                groupIdx = i;
                break;
            }
        }
        return {
            fillColor: groupIdx >= 0 ? colors[groupIdx % colors.length] : '#eee',
            weight: 1,
            color: '#999',
            fillOpacity: groupIdx >= 0 ? 0.6 : 0.2,
        };
    }
}

function getColor(minutes) {
    // Scale ตาม % share ของยอดรวมทั้งประเทศ (ตามที่ อ.เต้ เสนอ)
    // Bins: 0-5 / 5-10 / 10-15 / 15-20 / 20%+
    if (!provinceTotal || minutes === 0) return '#f0f0f0';
    const pct = (minutes / provinceTotal) * 100;
    if (pct >= 20) return '#08306b';   // ≥20% — เข้มสุด
    if (pct >= 15) return '#08519c';   // 15-20%
    if (pct >= 10) return '#2171b5';   // 10-15%
    if (pct >= 5)  return '#4292c6';   // 5-10%
    return '#9ecae1';                   // 0-5% — อ่อน
}

async function loadMarkers() {
    if (markerLayer) {
        map.removeLayer(markerLayer);
        markerLayer = null;
    }

    try {
        const res = await fetch('/api/markers');
        const data = await res.json();
        markerLayer = L.layerGroup();

        data.forEach(m => {
            const icon = m.type === 'branch'
                ? L.divIcon({ className: 'marker-branch', html: '<div class="pin pin-branch"></div>', iconSize: [24, 24], iconAnchor: [12, 24] })
                : L.divIcon({ className: 'marker-org', html: '<div class="pin pin-org"></div>', iconSize: [18, 18], iconAnchor: [9, 18] });

            let popup;
            if (m.type === 'branch') {
                popup = `<b>${m.name}</b><br>${m.province}<br>${FMT_MAP.format(m.minutes)} นาที (${m.records} รายการ)`;
            } else {
                popup = `<b>${m.name}</b><br>สาขา: ${m.branch}<br>${FMT_MAP.format(m.minutes)} นาที`;
            }

            L.marker([m.lat, m.lng], { icon })
                .bindPopup(popup)
                .addTo(markerLayer);
        });

        markerLayer.addTo(map);
    } catch (e) {
        console.error('markers error:', e);
    }
}

function clearMarkers() {
    if (markerLayer) {
        map.removeLayer(markerLayer);
        markerLayer = null;
    }
}

function switchMapView(view) {
    currentView = view;
    document.getElementById('btn-province').classList.toggle('active', view === 'province');
    document.getElementById('btn-group').classList.toggle('active', view === 'group');
    document.getElementById('btn-markers').classList.toggle('active', view === 'markers');

    if (geoLayer) {
        geoLayer.eachLayer(layer => {
            layer.setStyle(getProvinceStyle(layer.feature));
        });
    }

    if (view === 'markers') {
        loadMarkers();
    } else {
        clearMarkers();
    }
}

initMap();
