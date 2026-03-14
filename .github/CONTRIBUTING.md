# Contributing — วิทิสา 49M Dev

## Workflow

1. สร้าง Issue ก่อนเริ่มงาน (bug / feature / task)
2. สร้าง Branch จาก `main`
   ```bash
   git checkout -b feature/ชื่อ-งาน
   ```
3. พัฒนาและทดสอบในเครื่อง
   ```bash
   docker compose up -d
   cd services/api && python3 -m pytest tests/ -v
   ```
4. Commit ด้วยข้อความที่ชัดเจน
   ```
   feat: เพิ่ม endpoint ใหม่
   fix: แก้ปัญหา validation
   docs: อัพเดท spec
   test: เพิ่ม test case
   ```
5. Push และเปิด PR → CI จะรัน test อัตโนมัติ
6. รอ review จากทีม → merge เข้า `main`

## Branch Naming

| Prefix | ใช้เมื่อ | ตัวอย่าง |
|--------|---------|---------|
| `feature/` | เพิ่มฟีเจอร์ใหม่ | `feature/line-oa-webhook` |
| `fix/` | แก้ bug | `fix/anti-fraud-negative` |
| `docs/` | แก้เอกสาร | `docs/update-api-spec` |
| `test/` | เพิ่ม/แก้ test | `test/load-test` |

## โครงสร้าง Service

แต่ละ service อยู่ใน `services/` แยกกัน ใช้ Docker Compose modular (`include:` pattern)

```
services/
├── api/         # แก้ API, anti-fraud, business logic
├── dashboard/   # แก้ UI, แผนที่, CSS
├── db/          # แก้ schema, seed data, migration
├── adminer/     # ไม่ค่อยต้องแก้
└── tunnels/     # Cloudflare Tunnel config
```

## ก่อนเปิด PR

- [ ] `docker compose up -d` แล้วทดสอบในเครื่อง
- [ ] `python3 -m pytest tests/ -v` ผ่านทุก test
- [ ] อัพเดท spec/docs ถ้าแก้ API contract
