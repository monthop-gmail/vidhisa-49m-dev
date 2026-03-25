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
| `sub_district` | string | ตำบล/แขวง |
| `district` | string | อำเภอ/เขต |
| `province` | string | จังหวัด |
| `email` | string | อีเมลองค์กร |
| `max_participants` | integer | จำนวนผู้เข้าร่วมสูงสุด |
| `gender_male` | integer | จำนวนเพศชาย |
| `gender_female` | integer | จำนวนเพศหญิง |
| `gender_unspecified` | integer | จำนวนไม่ระบุเพศ |
| `contact_name` | string | ชื่อผู้ประสานงาน |
| `contact_phone` | string | เบอร์โทรผู้ประสานงาน |
| `contact_line_id` | string | LINE ID ผู้ประสานงาน |
| `enrolled_date` | date | วันที่สมัคร |
| `enrolled_until` | date | วันที่สิ้นสุดการสมัคร |
| `latitude` | double | ละติจูด |
| `longitude` | double | ลองจิจูด |
| `contact` | string | ข้อมูลติดต่อ (เดิม) |

> **กฎ:** เฉพาะ ORG-PLJ (สถาบันพลังจิตตานุภาพ) ที่มี `branch_id` — องค์กรภายนอก **ไม่สังกัดสาขา** (`branch_id = NULL`)

### 4. participants — ผู้เข้าร่วมรายบุคคล

| Field | Type | Description |
|-------|------|-------------|
| `id` | PK (SERIAL) | รหัสอัตโนมัติ |
| `branch_id` | FK → branches | สาขาที่สังกัด |
| `prefix` | string | คำนำหน้า เช่น นาย, นาง |
| `first_name` | string | ชื่อ |
| `last_name` | string | นามสกุล |
| `gender` | string | เพศ: male, female, unspecified |
| `age` | integer | อายุ |
| `sub_district` | string | ตำบล/แขวง |
| `district` | string | อำเภอ/เขต |
| `province` | string | จังหวัด |
| `phone` | string | เบอร์โทร |
| `line_id` | string | LINE ID |
| `enrolled_date` | date | วันที่ลงทะเบียน |
| `privacy_accepted` | boolean | ยอมรับนโยบายข้อมูลส่วนบุคคล |
| `created_at` | timestamp | |

### 5. records — บันทึกการปฏิบัติ

| Field | Type | Description |
|-------|------|-------------|
| `id` | PK (SERIAL) | รหัสบันทึก |
| `type` | enum | `individual` / `bulk` |
| `branch_id` | FK → branches | สาขาที่ดูแล |
| `org_id` | FK → organizations | องค์กรเจ้าของนาที |
| `participant_id` | FK → participants | ผู้เข้าร่วม (individual) |
| `name` | string | ชื่อผู้บันทึก / ชื่อองค์กร |
| `minutes` | integer | นาทีรวม |
| `participant_count` | integer | จำนวนคน (bulk only) |
| `minutes_per_person` | integer | นาทีต่อคน (bulk only) |
| `morning_male` | integer | จำนวนชาย รอบเช้า |
| `morning_female` | integer | จำนวนหญิง รอบเช้า |
| `morning_unspecified` | integer | จำนวนไม่ระบุ รอบเช้า |
| `afternoon_male` | integer | จำนวนชาย รอบกลางวัน |
| `afternoon_female` | integer | จำนวนหญิง รอบกลางวัน |
| `afternoon_unspecified` | integer | จำนวนไม่ระบุ รอบกลางวัน |
| `evening_male` | integer | จำนวนชาย รอบเย็น |
| `evening_female` | integer | จำนวนหญิง รอบเย็น |
| `evening_unspecified` | integer | จำนวนไม่ระบุ รอบเย็น |
| `date` | date | วันที่ปฏิบัติ |
| `photo_url` | string | URL รูปหลักฐาน (optional) |
| `submitted_by` | string | ผู้ส่ง |
| `submitted_phone` | string | เบอร์โทรผู้ส่ง |
| `status` | enum | `pending` / `approved` / `rejected` |
| `approved_by` | string | ผู้อนุมัติ |
| `flags` | array | เช่น `["daily_limit_reached"]` |
| `ip_address` | string | สำหรับ anti-fraud |
| `device_id` | string | สำหรับ anti-fraud |
| `created_at` | timestamp | |
| `updated_at` | timestamp | |

> **Upsert:** POST /api/records — ถ้า `branch_id + org_id + name + date` ซ้ำ → อัพเดตแทนสร้างใหม่

### 6. daily_stats — สรุปรายวัน (Materialized / Cache)

| Field | Type | Description |
|-------|------|-------------|
| `date` | PK | วันที่ |
| `total_minutes` | bigint | นาทีรวมทั้งหมด |
| `total_records` | integer | จำนวนบันทึก |
| `total_branches` | integer | จำนวนสาขาที่บันทึก |
| `cumulative_minutes` | bigint | ยอดสะสมถึงวันนี้ |

### 7. province_stats — สรุปรายจังหวัด (Materialized / Cache)

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
                            ├──── (N) participants     │
                            │           │ 1            │
                            │           │              │
                            │ N         │ N            │ N
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
