# vidhisa-49m-dev

ต้นแบบ (Prototype) ระบบบันทึกและประมวลผลโครงการวิทิสา 49 ล้านนาที

> Repo หลัก: [vidhisa-49m](https://github.com/monthop-gmail/vidhisa-49m) — เอกสาร, วาระประชุม, ภาพรวมโครงการ

## จุดประสงค์ของ Repo นี้

- พัฒนาต้นแบบเพื่อพิสูจน์แนวคิด (Proof of Concept)
- ทดสอบ API Contract ก่อนพัฒนาจริง
- ให้ทีม UI/Dashboard ทำงานคู่ขนานกับทีม Infra/API ได้

## Spec

| Spec                                     | รายละเอียด                                       |
| ---------------------------------------- | ------------------------------------------------ |
| [API Spec](spec/api-spec.md)             | API Contract — endpoint, request/response format |
| [Data Spec](spec/data-spec.md)           | โครงสร้างข้อมูล, ตาราง, ความสัมพันธ์             |
| [Prototype Spec](spec/prototype-spec.md) | ขอบเขตต้นแบบ, สิ่งที่ทำ/ไม่ทำ                    |
| [DB Diagram](spec/db-diagram.md)         | ER Diagram, ความสัมพันธ์, กฎการนับนาที           |

## Services

| Service       | Port     | รายละเอียด                                                                            |
| ------------- | -------- | ------------------------------------------------------------------------------------- |
| **Dashboard** | `8080`   | หน้า Dashboard หลัก — ตัวเลขสะสม, Progress Bar, Projection, แผนที่, Leaderboard, Feed |
| **ลงทะเบียน** | `8080`   | register.html — ลงทะเบียนผู้เข้าร่วม + องค์กร (?branch=B001)                         |
| **บันทึกผล**  | `8080`   | record.html — บันทึกนาทีสมาธิรายสาขา (?branch=B001)                                  |
| **API**       | `8000`   | FastAPI + Swagger UI (`/docs`) — ทุก endpoint ตาม [API Spec](spec/api-spec.md)        |
| **Adminer**   | `8081`   | Web UI จัดการ DB — ดู/แก้ข้อมูลได้โดยตรง                                              |
| **DB**        | internal | PostgreSQL 16 — ฐานข้อมูลหลัก                                                         |

## Quick Start (Development)

```bash
cp .env.example .env
docker compose up -d
```

เปิดดู:

- Dashboard: http://34.15.162.243:8080
- ลงทะเบียน: http://34.15.162.243:8080/register.html?branch=B001
- บันทึกผล: http://34.15.162.243:8080/record.html?branch=B001
- Admin: http://34.15.162.243:8080/admin.html
- API Docs: http://34.15.162.243:8000/docs
- Adminer: http://34.15.162.243:8081 (server: `vidhisa-db`, user: `vidhisa`, db: `vidhisa49m`)

## Testing

Integration test ทดสอบกับ API + DB จริง (ไม่ใช่ mock) — 126 cases ครอบคลุมทุก endpoint

```bash
# ต้อง docker compose up -d ก่อน
cd services/api
pip install -r requirements-test.txt
python3 -m pytest tests/ -v
```

| Test File               | Cases | ครอบคลุม                                       |
| ----------------------- | ----- | ---------------------------------------------- |
| `test_health.py`        | 3     | health, Swagger UI, OpenAPI                    |
| `test_stats.py`         | 5     | total, by-province, by-group, by-branch, daily |
| `test_projection.py`    | 2     | ค่าคาดการณ์ + สูตรคำนวณ                        |
| `test_leaderboard.py`   | 2     | branch ranking, org ranking                    |
| `test_feed.py`          | 2     | feed + default limit                           |
| `test_records.py`       | 15    | CRUD, anti-fraud, approve/reject, 404, registration check |
| `test_branch.py`        | 2     | pending list, empty branch                     |
| `test_organizations.py` | 16    | CRUD, import/export CSV, duplicate, markers    |
| `test_branches.py`      | 14    | CRUD, import/export CSV, duplicate, stats      |
| `test_sse.py`           | 6     | pub/sub events, subscribe/unsubscribe          |
| `test_markers.py`       | 2     | map markers (branch + org)                     |
| `test_participants.py`  | 17    | CRUD, import/export CSV, filter, duplicate, transfer |
| `test_records_extended.py` | 15 | list+filter, export, import, upsert, 9 fields  |
| `test_admin_flow.py`   | 12    | approve flow: org/participant/record pending→approved→record |
| `test_edge_cases.py`   | 13    | transfer, pagination, re-approve, upsert+approved, GGS |

## Production Deployment

ใช้ Docker Compose overlay เพื่อ deploy บน production server

```bash
# Build และ Run ด้วย Production Dockerfile
docker compose -f docker-compose.yml -f docker-compose.prd.yml up -d

# Rebuild ใหม่ทั้งหมด (เมื่อมีการเปลี่ยนแปลง)
docker compose -f docker-compose.yml -f docker-compose.prd.yml build --no-cache
docker compose -f docker-compose.yml -f docker-compose.prd.yml up -d

# Rebuild เฉพาะ API
docker compose -f docker-compose.yml -f docker-compose.prd.yml build vidhisa-api --no-cache
docker compose -f docker-compose.yml -f docker-compose.prd.yml up -d vidhisa-api
```

### Health Check

Production API มี health check endpoint ที่ `/api/healthz` สำหรับ container orchestration:

```bash
# ตรวจสอบ health status
curl http://localhost:8000/api/healthz
# Response: {"status":"ok","timestamp":"2026-03-22T02:40:00.000000+00:00","version":"0.1.0"}
```

### Logs

```bash
# ดู logs ทั้งหมด
docker compose -f docker-compose.yml -f docker-compose.prd.yml logs -f

# ดู logs เฉพาะ API
docker compose -f docker-compose.yml -f docker-compose.prd.yml logs -f vidhisa-api

# ดู logs แบบ tail
docker compose -f docker-compose.yml -f docker-compose.prd.yml logs --tail=100 vidhisa-api
```

## โครงสร้าง

```
vidhisa-49m-dev/
├── docker-compose.yml     # Root orchestrator (include pattern)
├── docker-compose.prd.yml # Production overlay (4 workers, non-root, health check)
├── .env.example           # ตัวแปร environment
├── spec/                  # Spec เอกสาร
│   ├── api-spec.md
│   ├── data-spec.md
│   ├── db-diagram.md
│   └── prototype-spec.md
└── services/              # Modular Docker Compose
    ├── api/               # FastAPI + anti-fraud
    │   └── tests/         # Integration test (126 cases)
    ├── db/                # PostgreSQL 16 + schema + seed data
    ├── dashboard/         # nginx + static HTML/JS (Leaflet map, register, record)
    ├── adminer/           # Adminer — Web DB management
    └── tunnels/           # Cloudflare Tunnels (placeholder)
```
