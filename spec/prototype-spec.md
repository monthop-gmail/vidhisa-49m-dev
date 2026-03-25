# Prototype Spec — วิทิสา 49 ล้านนาที

> สถานะ: **Phase 2 เสร็จ** — ระบบต้นแบบใช้งานได้ครบ

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

### Phase 2: API จริง + Database ✅

| งาน | รายละเอียด | สถานะ |
|-----|-----------|-------|
| **API Server** | FastAPI — บันทึก, สถิติ, คาดการณ์, leaderboard | ✅ เสร็จ |
| **Database** | PostgreSQL 16 + schema + seed data | ✅ เสร็จ |
| **Anti-fraud** | Rule-based validation (session/daily/cooldown/bulk) | ✅ เสร็จ |
| **สาขา Admin** | หน้าตรวจสอบ/อนุมัติยอด | ✅ เสร็จ |
| **องค์กร CRUD** | CRUD + Import/Export CSV องค์กร (รวม sub_district, district, email, max_participants, gender, contact, enrolled) | ✅ เสร็จ |
| **สาขา CRUD** | CRUD + Import/Export CSV สาขา | ✅ เสร็จ |
| **ผู้เข้าร่วม CRUD** | CRUD + Import/Export CSV ผู้เข้าร่วมรายบุคคล (participants) | ✅ เสร็จ |
| **บันทึก List/Export/Import** | GET /api/records, CSV export/import (upsert by branch+org+name+date) | ✅ เสร็จ |
| **Records 9 ฟิลด์** | แทน session booleans ด้วย morning/afternoon/evening × male/female/unspecified (9 ฟิลด์ int) | ✅ เสร็จ |
| **SSE Real-time** | Server-Sent Events — Dashboard refresh อัตโนมัติ | ✅ เสร็จ |
| **Adminer** | Web UI จัดการ DB โดยตรง (port 8081) | ✅ เสร็จ |

### Phase 3: Integration + Load Test

| งาน | รายละเอียด | สถานะ |
|-----|-----------|-------|
| **เชื่อม UI ↔ API จริง** | Dashboard เรียก API จริงจาก DB | ✅ เสร็จ |
| **หน้าลงทะเบียน** | register.html — ลงทะเบียนผู้เข้าร่วม + องค์กร (?branch=B001) | ✅ เสร็จ |
| **หน้าบันทึกผล** | record.html — บันทึกนาทีสมาธิรายสาขา (?branch=B001) | ✅ เสร็จ |
| **Integration Test** | 94 test cases ครอบคลุมทุก endpoint + anti-fraud + CRUD + import/export + participants + upsert | ✅ เสร็จ |
| **Load Test** | จำลอง concurrent users ระดับหมื่น-แสน | ⬜ รอดำเนินการ |
| **DB Diagram** | ER diagram + กฎการนับนาที + Business Rules | ✅ เสร็จ |
| **Infra** | Docker Compose modular + CF Tunnel | ✅ modular เสร็จ / CF Tunnel placeholder |

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
| **Backend API** | FastAPI (Python 3.12) + async SQLAlchemy | รองรับ concurrent สูง |
| **Database** | PostgreSQL 16 | เหมาะกับ analytics + scale |
| **Map** | Leaflet + Thailand GeoJSON | Open source, ไม่มีค่าใช้จ่าย |
| **DB Management** | Adminer | Web UI ดู/แก้ข้อมูลได้ทันที |
| **Infra** | Docker Compose modular (include pattern) | ตาม checklist 74 ข้อ |
| **Testing** | pytest + httpx (integration test กับ DB จริง) | ไม่ใช้ mock, ทดสอบ end-to-end |

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

> สถานะ: **Phase 2 เสร็จ** — ระบบต้นแบบใช้งานได้ครบ
