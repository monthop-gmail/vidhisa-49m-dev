# vithisa-49m-dev

ต้นแบบ (Prototype) ระบบบันทึกและประมวลผลโครงการวิทิสา 49 ล้านนาที

> Repo หลัก: [vithisa-49m](https://github.com/monthop-gmail/vithisa-49m) — เอกสาร, วาระประชุม, ภาพรวมโครงการ

## จุดประสงค์ของ Repo นี้

- พัฒนาต้นแบบเพื่อพิสูจน์แนวคิด (Proof of Concept)
- ทดสอบ API Contract ก่อนพัฒนาจริง
- ให้ทีม UI/Dashboard ทำงานคู่ขนานกับทีม Infra/API ได้

## Spec

| Spec | รายละเอียด |
|------|-----------|
| [API Spec](spec/api-spec.md) | API Contract — endpoint, request/response format |
| [Data Spec](spec/data-spec.md) | โครงสร้างข้อมูล, ตาราง, ความสัมพันธ์ |
| [Prototype Spec](spec/prototype-spec.md) | ขอบเขตต้นแบบ, สิ่งที่ทำ/ไม่ทำ |

## Services

| Service | Port | รายละเอียด |
|---------|------|-----------|
| **Dashboard** | `8080` | หน้า Dashboard หลัก — ตัวเลขสะสม, Progress Bar, Projection, แผนที่, Leaderboard, Feed |
| **API** | `8000` | FastAPI + Swagger UI (`/docs`) — ทุก endpoint ตาม [API Spec](spec/api-spec.md) |
| **Adminer** | `8081` | Web UI จัดการ DB — ดู/แก้ข้อมูลได้โดยตรง |
| **DB** | internal | PostgreSQL 16 — ฐานข้อมูลหลัก |

## Quick Start

```bash
cp .env.example .env
docker compose up -d
```

เปิดดู:
- Dashboard: http://localhost:8080
- API Docs: http://localhost:8000/docs
- Adminer: http://localhost:8081 (server: `vithisa-db`, user: `vithisa`, pass: `changeme`, db: `vithisa49m`)

## โครงสร้าง

```
vithisa-49m-dev/
├── docker-compose.yml     # Root orchestrator (include pattern)
├── .env.example           # ตัวแปร environment
├── spec/                  # Spec เอกสาร
│   ├── api-spec.md
│   ├── data-spec.md
│   └── prototype-spec.md
└── services/              # Modular Docker Compose
    ├── api/               # FastAPI + anti-fraud
    ├── db/                # PostgreSQL 16 + schema + seed data
    ├── dashboard/         # nginx + static HTML/JS (Leaflet map)
    ├── adminer/           # Adminer — Web DB management
    └── tunnels/           # Cloudflare Tunnels (placeholder)
```
