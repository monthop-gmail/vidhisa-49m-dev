let map, geoLayer;
let provinceData = {};
let groupData = [];
let currentView = 'province';

function initMap() {
    map = L.map('map').setView([13.0, 101.0], 6);
    L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
        attribution: '&copy; OpenStreetMap',
        maxZoom: 10,
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

        geoLayer = L.geoJSON(geo, {
            style: feature => getProvinceStyle(feature),
            onEachFeature: (feature, layer) => {
                layer.on('mouseover', function (e) {
                    const code = getProvinceCode(feature);
                    const data = provinceData[code];
                    const name = feature.properties.NAME_1 || feature.properties.name || code;
                    const minutes = data ? new Intl.NumberFormat('th-TH').format(data.minutes) : '0';
                    layer.bindTooltip(`${name}<br>${minutes} นาที`).openTooltip();
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
    // Try common GeoJSON property names for ISO code
    return feature.properties.ISO_3166_2 ||
           feature.properties.iso_3166_2 ||
           feature.properties.CC_2 ||
           ('TH-' + (feature.properties.ID_1 || ''));
}

function getProvinceStyle(feature) {
    const code = getProvinceCode(feature);

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
        // Group view — find which group this province belongs to
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
    if (minutes > 10000) return '#08306b';
    if (minutes > 5000) return '#2171b5';
    if (minutes > 2000) return '#4292c6';
    if (minutes > 1000) return '#6baed6';
    if (minutes > 500) return '#9ecae1';
    if (minutes > 0) return '#c6dbef';
    return '#f0f0f0';
}

function switchMapView(view) {
    currentView = view;
    document.getElementById('btn-province').classList.toggle('active', view === 'province');
    document.getElementById('btn-group').classList.toggle('active', view === 'group');

    if (geoLayer) {
        geoLayer.eachLayer(layer => {
            const style = getProvinceStyle(layer.feature);
            layer.setStyle(style);
        });
    }
}

initMap();
