# CLAUDE.md — vidhisa-49m-dev (ระบบต้นแบบ)

## บทบาทของ AI ใน Repo นี้

คุณคือ **นักพัฒนา (Developer)** ของระบบต้นแบบวิทิสา 49 ล้านนาที

**หน้าที่หลัก:**

- เขียนและแก้ไขโค้ด (API, Dashboard, DB schema, tests)
- ออกแบบ endpoint, data model, business logic
- เขียน integration test ครอบคลุมทุก endpoint (ห้าม mock)
- ดูแล Docker Compose ให้ทำงานได้ถูกต้อง
- รักษาความสอดคล้องระหว่างโค้ดกับ spec

**สิ่งที่ต้องระวัง:**

- ตรวจสอบ business rules ก่อนเขียนโค้ด (ดูหัวข้อ "กฎสำคัญ" ด้านล่าง)
- รัน test ทุกครั้งหลังแก้โค้ด — ต้อง pass ทั้งหมดก่อน commit
- อัพเดท spec (`spec/*.md`) ให้ตรงกับโค้ดเสมอ
- แก้ไขไฟล์เดิมก่อนสร้างใหม่

## โครงการ

โครงการวิทิสา 49 ล้านนาที — ระบบบันทึกและประมวลผลการปฏิบัติสมาธิวิทิสา

- **Deadline:** 2026-07-31
- **Docs repo:** [vidhisa-49m](https://github.com/monthop-gmail/vidhisa-49m) — เอกสาร, วาระประชุม

## Quick Start

```bash
cp .env.example .env
docker compose up -d
```

- Dashboard: http://localhost:8080
- API Docs: http://localhost:8000/docs
- Adminer: http://localhost:8081

## โครงสร้าง

```
docker-compose.yml          # Root orchestrator (include pattern)
services/
  api/                      # FastAPI (Python 3.12)
    app/config.py            # ค่าคงที่: target, deadline, anti-fraud limits
    app/anti_fraud.py        # Validation rules
    app/routers/             # Endpoint ทั้งหมด
    tests/                   # Integration test (94 cases, ทดสอบกับ DB จริง)
  db/init/                   # 01-schema.sql → 02-branches.sql → 03-seed.sql
  dashboard/html/            # Static HTML/JS/CSS (nginx)
  adminer/                   # Adminer — Web DB management
  tunnels/                   # Cloudflare Tunnel (placeholder)
spec/
  api-spec.md                # API Contract ทุก endpoint
  data-spec.md               # โครงสร้างตาราง + ความสัมพันธ์
  db-diagram.md              # ER diagram + Business Rules
  prototype-spec.md          # ขอบเขตต้นแบบ
```

## วิทิสาสมาธิ (Domain Knowledge)

- เป็นรูปแบบหนึ่งของการปฏิบัติสมาธิ
- ครั้งละ **5 นาที**, สูงสุด **3 ครั้ง/วัน** (เช้า กลางวัน เย็น)
- เพดานต่อคน = 15 นาที/วัน

## คำศัพท์

| คำ                       | ความหมาย                                                        |
| ------------------------ | --------------------------------------------------------------- |
| สาขา (branch)            | สาขาสถาบันพลังจิตตานุภาพ ~305 แห่ง                              |
| กลุ่มสาขา (branch_group) | กลุ่มรวมสาขา ~30 กลุ่ม จัดตามภูมิภาค                            |
| ORG-PLJ                  | สถาบันพลังจิตตานุภาพ — องค์กรพิเศษที่เชื่อมกับสาขา              |
| องค์กรภายนอก             | โรงเรียน/วัด/มหาวิทยาลัย — **ต้องลงทะเบียนกับสาขา** |

## กฎสำคัญ

### Data Model

- องค์กรภายนอก **ต้องลงทะเบียนกับสาขา** (`branch_id` มีค่าทุกองค์กร) — สาขาเป็นผู้บันทึกให้
- นาทีเป็นขององค์กรภายนอก — **ไม่นับเข้ารายสาขา** (การนับคงเดิม)

### การนับนาที (Business Rules)

- ยอดรวม = สถาบันฯ (ORG-PLJ) + องค์กรภายนอก
- รายสาขา/กลุ่มสาขา = เฉพาะ `org_id = 'ORG-PLJ'`
- รายจังหวัด = รวมทั้งหมด (สาขา + องค์กร)

### Anti-fraud Limits (config.py)

- `MAX_SESSION_MINUTES = 5` — วิทิสาสมาธิครั้งละ 5 นาที
- `MAX_DAILY_MINUTES = 15` — 3 ครั้ง/วัน
- `MAX_BULK_MINUTES_PER_PERSON = 5`
- `COOLDOWN_SECONDS = 0` — ✅ ยืนยันไม่ใช้

## การทดสอบ

```bash
# ต้อง docker compose up -d ก่อน
docker compose exec vidhisa-api python3 -m pytest tests/ -v
```

- ใช้ integration test กับ DB จริง — **ห้ามใช้ mock**
- 98 test cases ครอบคลุมทุก endpoint

## แนวทางการพัฒนา

- **Modular Docker Compose** — ใช้ `include` pattern เสมอ, 1 service = 1 compose.yaml
- **ไม่มี Login/Auth** — ตามแนวทาง อ.เต้
- Commit message ภาษาไทย, prefix: `feat:`, `fix:`, `docs:`, `test:`
- เมื่อแก้ schema หรือ seed data → ต้อง `docker compose down -v && docker compose up -d`
- เมื่อเพิ่ม dependency → ต้อง `docker compose build --no-cache vidhisa-api`
- Route ordering: static routes (`/export`, `/import`) ต้องอยู่ **ก่อน** parameterized routes (`/{id}`)
- CSV import/export ใช้ UTF-8 BOM สำหรับ Excel compatibility

## Code Style (Python)

ใช้ ruff เป็น linter และ formatter เพียงตัวเดียว

```bash
# Lint และ format
ruff check --fix services/api/app/
ruff format services/api/app/

# ติดตั้ง dependency
pip install ruff mypy
```

### การตั้งค่า (`services/api/pyproject.toml`)

```toml
[tool.ruff]
line-length = 120
target-version = "py312"

[tool.ruff.lint]
select = ["E", "W", "F", "I", "B", "C4", "UP", "SIM", "ANN"]
ignore = ["E501", "ANN401"]
```

### มาตรฐานการเขียน

- **Type hints** สำหรับทุก function และ class
- **Docstrings** แบบ Google style สำหรับ public API
- **Naming**: snake_case สำหรับ functions/variables, PascalCase สำหรับ classes
- **Imports**: จัดลำดับ standard library → third-party → local
- **Column definitions** ใน models.py: ใช้ `Column(...)` wrapper เสมอ

```python
# ถูกต้อง
id = Column(String(10), primary_key=True)

# ผิด - จะ error เพราะ String() ไม่รับ primary_key
id = String(10, primary_key=True)
```
