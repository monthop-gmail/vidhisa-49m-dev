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

## โครงสร้าง (Planned)

```
vithisa-49m-dev/
├── spec/                  # Spec เอกสาร
├── mock/                  # Mock API + ข้อมูลตัวอย่าง
├── prototype/             # ต้นแบบ UI/Dashboard
└── services/              # Modular Docker Compose (เมื่อพร้อม)
    ├── api/
    ├── db/
    ├── dashboard/
    └── tunnels/
```
