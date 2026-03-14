# Prototype Spec — วิทิสา 49 ล้านนาที

> สถานะ: **ร่าง** — รอหารือในที่ประชุม

---

## จุดประสงค์

สร้างต้นแบบเพื่อ:
1. พิสูจน์แนวคิดก่อนพัฒนาจริง
2. ใช้ประกอบการนำเสนอในที่ประชุม
3. ให้ทีม UI/Dashboard ทำงานคู่ขนานกับทีม API ได้

---

## สิ่งที่ทำ (In Scope)

### Phase 1: Mock + UI ต้นแบบ

| ต้นแบบ | รายละเอียด | อ้างอิง |
|--------|-----------|--------|
| **Mock API** | JSON responses ตาม API Spec ให้ทีม UI เรียกใช้ได้ | [api-spec.md](api-spec.md) |
| **Dashboard** | แสดงตัวเลขสะสม + Progress Bar + Projection | draft-001 ส่วนที่ ๑, ๓, ๕ |
| **แผนที่ประเทศไทย** | Heat Map รายจังหวัด + Hover tooltip | draft-001 ส่วนที่ ๒ |
| **Live Feed** | Ticker แสดงบันทึกล่าสุด (mock data) | draft-001 ส่วนที่ ๔ |

### Phase 2: API จริง + Database

| งาน | รายละเอียด |
|-----|-----------|
| **API Server** | ตาม API Spec — บันทึก, สถิติ, คาดการณ์, leaderboard |
| **Database** | ตาม Data Spec — PostgreSQL |
| **Anti-fraud** | Rule-based validation ตาม API Spec |
| **สาขา Admin** | หน้าตรวจสอบ/อนุมัติยอด |

### Phase 3: Integration + Load Test

| งาน | รายละเอียด |
|-----|-----------|
| **เชื่อม UI ↔ API จริง** | เปลี่ยนจาก mock เป็น API จริง |
| **Load Test** | จำลอง concurrent users ระดับหมื่น-แสน |
| **Infra** | Docker Compose modular + CF Tunnel |

---

## สิ่งที่ยังไม่ทำ (Out of Scope)

| รายการ | เหตุผล |
|--------|--------|
| LINE OA integration | รอสรุปแนวทางจากที่ประชุม |
| Multi-language | ไม่ใช่ priority แรก |
| แผนที่โลก (Global) | ทำทีหลังได้ |
| โพสต์การ์ดถวายพระพร | ไม่ใช่ core feature |
| Login / Authentication | ตามแนวทาง อ.เต้ — ไม่ใช้ login |

---

## เทคโนโลยี (เสนอ)

| Layer | เทคโนโลยี | เหตุผล |
|-------|----------|--------|
| **Frontend** | HTML + JS (หรือตามทีม UI เลือก) | เรียก API ได้ทุกแบบ |
| **Mock API** | JSON file / json-server | ทีม UI ใช้ได้ทันที |
| **Backend API** | TBD (รอหารือ) | ต้องรองรับ concurrent สูง |
| **Database** | PostgreSQL | เหมาะกับ analytics + scale |
| **Map** | Leaflet + Thailand GeoJSON | Open source, ไม่มีค่าใช้จ่าย |
| **Infra** | Docker Compose modular | ตาม checklist 74 ข้อ |

---

## แนวทางทำงานคู่ขนาน (Parallel Development)

```
ตกลง API Contract (spec/api-spec.md)
              │
     ┌────────┴────────┐
     ▼                  ▼
ทีม Infra/API      ทีม UI/Dashboard
  │                    │
  ├─ สร้าง Mock API    ├─ สร้าง UI เรียก Mock
  ├─ สร้าง DB schema   ├─ Dashboard + Map
  ├─ สร้าง API จริง    ├─ Live Feed + Leaderboard
  ├─ Anti-fraud rules  │
  │                    │
  └────────┬───────────┘
           ▼
    เชื่อม UI ↔ API จริง
           │
           ▼
      Load Test + Go-live
```

---

> สถานะ: **ร่าง** — รอหารือในที่ประชุม
