# Data Spec — วิทิสา 49 ล้านนาที

> สถานะ: **ร่าง** — รอหารือในที่ประชุม

---

## ตาราง

### 1. branch_groups — กลุ่มสาขา (~30 กลุ่ม)

| Field | Type | Description |
|-------|------|-------------|
| `id` | PK | รหัสกลุ่ม เช่น G08 |
| `name` | string | ชื่อกลุ่ม เช่น "กลุ่ม 8" |
| `provinces` | array | จังหวัดในกลุ่ม เช่น `["TH-76","TH-70","TH-75"]` |

> ตัวอย่าง: กลุ่ม 8 → เพชรบุรี, ราชบุรี, สมุทรสงคราม
>
> ข้อมูลกลุ่มทั้งหมด **ต้องขอจากทีม** (อ.เต้ / อ.จีรกาญ)

### 2. branches — สาขา (~305 สาขา)

| Field | Type | Description |
|-------|------|-------------|
| `id` | PK | รหัสสาขา เช่น B001 |
| `name` | string | ชื่อสาขา |
| `group_id` | FK → branch_groups | กลุ่มที่สังกัด |
| `province` | string | จังหวัด |
| `province_code` | string | รหัสจังหวัด ISO 3166-2 เช่น TH-10 |
| `admin_name` | string | ชื่อผู้ดูแลสาขา |
| `contact` | string | ช่องทางติดต่อ |
| `created_at` | timestamp | |

### 3. organizations — องค์กร

| Field | Type | Description |
|-------|------|-------------|
| `id` | PK | รหัสองค์กร เช่น ORG-PLJ, ORG001 |
| `name` | string | ชื่อองค์กร |
| `org_type` | string | ประเภท: สถาบันพลังจิตตานุภาพ, โรงเรียน, มหาวิทยาลัย, วัด, หน่วยงาน, ชุมชน |
| `branch_id` | FK → branches (optional) | สาขาที่สังกัด — เฉพาะ ORG-PLJ, องค์กรภายนอก = NULL |
| `province` | string | จังหวัด |
| `latitude` | double | ละติจูด |
| `longitude` | double | ลองจิจูด |
| `contact` | string | ข้อมูลติดต่อ |

> **กฎ:** เฉพาะ ORG-PLJ (สถาบันพลังจิตตานุภาพ) ที่มี `branch_id` — องค์กรภายนอก **ไม่สังกัดสาขา** (`branch_id = NULL`)

### 4. records — บันทึกการปฏิบัติ

| Field | Type | Description |
|-------|------|-------------|
| `id` | PK | รหัสบันทึก |
| `type` | enum | `individual` / `bulk` |
| `branch_id` | FK → branches | สาขาที่ดูแล |
| `org_id` | FK → organizations | องค์กรเจ้าของนาที |
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

### 5. daily_stats — สรุปรายวัน (Materialized / Cache)

| Field | Type | Description |
|-------|------|-------------|
| `date` | PK | วันที่ |
| `total_minutes` | bigint | นาทีรวมทั้งหมด |
| `total_records` | integer | จำนวนบันทึก |
| `total_branches` | integer | จำนวนสาขาที่บันทึก |
| `cumulative_minutes` | bigint | ยอดสะสมถึงวันนี้ |

### 6. province_stats — สรุปรายจังหวัด (Materialized / Cache)

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
branch_groups (1) ──── (N) branches (1) ──── (N) organizations (optional, เฉพาะ ORG-PLJ)
                            │ 1                        │ 1
                            │                          │
                            │ N                        │ N
                            └───────── records ────────┘
```

> ดู [db-diagram.md](db-diagram.md) สำหรับ ER diagram และกฎการนับนาทีแบบละเอียด

### Map 2 มุมมอง

```
มุมมอง "จังหวัด"          มุมมอง "กลุ่มสาขา"
  77 จังหวัด                30 กลุ่ม
  province_stats             group by branch_groups.provinces
  Heat Map สีตามยอดจังหวัด   Heat Map สีตามยอดกลุ่ม
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
| กลุ่มสาขา | ~30 rows |
| สาขา | ~305 rows |
| จังหวัด | 77 rows |
| บันทึกต่อวัน (peak) | ~100,000 records |
| บันทึกตลอดโครงการ (~120 วัน) | ~5,000,000 records |
| ขนาด DB โดยประมาณ | ~2-5 GB |

---

> สถานะ: **ร่าง** — รอหารือในที่ประชุม
