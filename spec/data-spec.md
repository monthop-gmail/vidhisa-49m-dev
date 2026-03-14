# Data Spec — วิทิสา 49 ล้านนาที

> สถานะ: **ร่าง** — รอหารือในที่ประชุม

---

## ตาราง

### 1. branches — สาขา

| Field | Type | Description |
|-------|------|-------------|
| `id` | PK | รหัสสาขา เช่น B001 |
| `name` | string | ชื่อสาขา |
| `province` | string | จังหวัด |
| `province_code` | string | รหัสจังหวัด ISO 3166-2 เช่น TH-10 |
| `admin_name` | string | ชื่อผู้ดูแลสาขา |
| `contact` | string | ช่องทางติดต่อ |
| `created_at` | timestamp | |

### 2. records — บันทึกการปฏิบัติ

| Field | Type | Description |
|-------|------|-------------|
| `id` | PK | รหัสบันทึก |
| `type` | enum | `individual` / `bulk` |
| `branch_id` | FK → branches | สาขาที่ดูแล |
| `name` | string | ชื่อผู้บันทึก / ชื่อองค์กร |
| `minutes` | integer | นาทีรวม |
| `participant_count` | integer | จำนวนคน (bulk only) |
| `minutes_per_person` | integer | นาทีต่อคน (bulk only) |
| `date` | date | วันที่ปฏิบัติ |
| `photo_url` | string | URL รูปหลักฐาน (optional) |
| `submitted_by` | string | ผู้ส่ง |
| `status` | enum | `pending` / `approved` / `rejected` |
| `approved_by` | string | ผู้อนุมัติ |
| `flags` | array | เช่น `["daily_limit_reached"]` |
| `ip_address` | string | สำหรับ anti-fraud |
| `device_id` | string | สำหรับ anti-fraud |
| `created_at` | timestamp | |
| `updated_at` | timestamp | |

### 3. daily_stats — สรุปรายวัน (Materialized / Cache)

| Field | Type | Description |
|-------|------|-------------|
| `date` | PK | วันที่ |
| `total_minutes` | bigint | นาทีรวมทั้งหมด |
| `total_records` | integer | จำนวนบันทึก |
| `total_branches` | integer | จำนวนสาขาที่บันทึก |
| `cumulative_minutes` | bigint | ยอดสะสมถึงวันนี้ |

### 4. province_stats — สรุปรายจังหวัด (Materialized / Cache)

| Field | Type | Description |
|-------|------|-------------|
| `province_code` | PK | รหัสจังหวัด |
| `province` | string | ชื่อจังหวัด |
| `total_minutes` | bigint | นาทีรวม |
| `total_records` | integer | จำนวนบันทึก |
| `last_updated` | timestamp | |

---

## ความสัมพันธ์

```
branches (1) ──── (N) records
    │
    └── province_code ──── province_stats
```

---

## Anti-fraud Fields

ข้อมูลที่เก็บเพื่อใช้ตรวจจับความผิดปกติ:

| Field | ใช้ตรวจจับ |
|-------|----------|
| `ip_address` | หลายคนจาก IP เดียวกัน |
| `device_id` | หลายคนจาก device เดียวกัน |
| `created_at` | บันทึกเป็นจังหวะซ้ำๆ / เวลาผิดปกติ |
| `minutes` + `date` | เกินเพดานต่อวัน |
| `flags` | ระบบ flag อัตโนมัติ → สาขา review |

---

## ประมาณขนาดข้อมูล

| รายการ | ประมาณการ |
|--------|----------|
| สาขา | ~305 rows |
| จังหวัด | 77 rows |
| บันทึกต่อวัน (peak) | ~100,000 records |
| บันทึกตลอดโครงการ (~120 วัน) | ~5,000,000 records |
| ขนาด DB โดยประมาณ | ~2-5 GB |

---

> สถานะ: **ร่าง** — รอหารือในที่ประชุม
