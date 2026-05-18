# Data Spec — วิทิสา 49 ล้านนาที

> สถานะ: **implemented + deployed** — สะท้อนสถานะ schema จริงบน main branch

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

### 2. branches — สาขา (325 สาขา)

| Field | Type | Description |
|-------|------|-------------|
| `id` | PK | รหัสสาขา เช่น B001 |
| `name` | string | ชื่อสาขา |
| `group_id` | FK → branch_groups | กลุ่มที่สังกัด |
| `custom_region` | string | ภูมิภาคจัดกลุ่มเอง |
| `sub_district` | string | ตำบล/แขวง |
| `district` | string | อำเภอ/เขต |
| `province` | string | จังหวัด |
| `province_code` | string | รหัสจังหวัด ISO 3166-2 เช่น TH-10 |
| `latitude` | double | ละติจูด |
| `longitude` | double | ลองจิจูด |
| `admin_name` | string | ชื่อผู้ดูแลสาขา |
| `contact` | string | ช่องทางติดต่อ |
| `opening_hours` | string | เวลาทำการ |
| `ggs_url_org` | text | URL Google Sheet ลงทะเบียนหน่วยงาน (per-branch) |
| `ggs_url_participant` | text | URL Google Sheet ลงทะเบียนรายบุคคล |
| `ggs_url_record_bulk` | text | URL Google Sheet บันทึกแบบกลุ่ม |
| `ggs_url_record_ind` | text | URL Google Sheet บันทึกรายบุคคล |
| `view_secret` | varchar(6) UNIQUE NOT NULL | secret สำหรับ me-ui (Crockford base32) |
| `record_form_url` | varchar(500) | URL Google Form ให้ผู้เข้าร่วมกรอกบันทึก |
| `created_at` | timestamp | |

### 3. organizations — องค์กร

| Field | Type | Description |
|-------|------|-------------|
| `id` | PK | รหัสองค์กร: `B{xxx}-00` = สถาบันพลังจิตตานุภาพ (PLJ — auto-create ตอน approve enrollment) / `B{xxx}-NN` = องค์กรภายนอก (NN ≥ 01) |
| `name` | string | ชื่อองค์กร |
| `org_type` | string | ประเภท: สถาบันพลังจิตตานุภาพ, โรงเรียน, มหาวิทยาลัย, วัด, หน่วยงาน, ชุมชน |
| `branch_id` | FK → branches | สาขาที่ลงทะเบียน — ทุกองค์กรต้องมี |
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

> **กฎ:** ทุกองค์กรต้องลงทะเบียนกับสาขา (`branch_id` มีค่าทุกตัว) — สาขาเป็นผู้บันทึก, นาทีเป็นขององค์กร

### 4. participants — ผู้เข้าร่วมรายบุคคล

| Field | Type | Description |
|-------|------|-------------|
| `id` | PK (SERIAL) | รหัสอัตโนมัติ |
| `branch_id` | FK → branches | สาขาที่สังกัด |
| `member_code` | string(20) | รหัสในสาขา (เช่น "001" — สกัดจาก prefix ชื่อใน GGS sync) |
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
| `status` | enum | `pending` / `approved` / `rejected` (auto-sync จาก GGS สร้างเป็น `approved`) |
| `created_at` | timestamp | |

> **กฎ 1 คน 1 สาขา:** ชื่อ `first_name + last_name` ซ้ำข้ามสาขาไม่ได้ — GGS sync จะ skip row + log error

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

### 8. users — บัญชีผู้ใช้ (admin)

| Field | Type | Description |
|-------|------|-------------|
| `id` | PK (SERIAL) | |
| `username` | string UNIQUE | login id (มักเป็น email สำหรับ branch_admin) |
| `password_hash` | string | bcrypt hash |
| `full_name` | string | |
| `email` | string | |
| `phone` | string | เบอร์โทร |
| `role` | enum | `central_admin` / `branch_admin` |
| `branch_id` | FK → branches | สาขาที่ดูแล (branch_admin เท่านั้น) |
| `status` | enum | `active` / `disabled` |

### 9. branch_enrollments — สาขาขอเข้าร่วมโครงการ

| Field | Type | Description |
|-------|------|-------------|
| `id` | PK (SERIAL) | |
| `branch_number` | string | "001" รูปแบบ 3 หลัก (zfill) |
| `branch_name` | string | |
| `admin1_name` / `admin1_email` / `admin1_phone` | string | ผู้ประสานงาน 1 |
| `admin2_name` / ... | string | ผู้ประสานงาน 2 |
| `admin3_name` / ... | string | ผู้ประสานงาน 3 |
| `submitted_email` | string | email ผู้ส่งฟอร์ม |
| `submitted_at` | timestamp | |
| `status` | enum | `pending` / `approved` / `rejected` |
| `approved_at` | timestamp | |

> ตอน approve → สร้าง users 3 บัญชี (1 ต่อ admin) + สร้าง PLJ org (`B{xxx}-00`) auto-approved

### 10. branch_view_log — audit log สำหรับ me-ui

| Field | Type | Description |
|-------|------|-------------|
| `id` | PK BIGSERIAL | |
| `ts` | timestamptz | |
| `branch_id` | string(10) | |
| `ip` | string(45) | client IP |
| `action` | string(20) | `info` / `search` / `me` / `invalid` |
| `participant_id` | int nullable | |
| `status_code` | int | 200 / 404 / 429 |
| `user_agent` | string(500) | |

> ใช้ตรวจ rate limit + brute force attempts (ดู branch-view-api-spec.md)

---

## ความสัมพันธ์

```
branch_groups (1) ──── (N) branches (1) ──── (N) organizations (PLJ-Bxxx auto-create + องค์กรภายนอก)
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

> สถานะ: **implemented + deployed** — สะท้อน schema จริงบน main branch
