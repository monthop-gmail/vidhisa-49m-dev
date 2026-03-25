# Database Diagram — วิทิสา 49 ล้านนาที

## ER Diagram

```
┌─────────────────┐
│  branch_groups  │
│─────────────────│
│ PK id           │
│    name         │
│    provinces[]   │
└────────┬────────┘
         │ 1
         │
         │ ∞
┌────────┴────────┐         ┌──────────────────────┐
│    branches     │ 1     ∞ │    organizations     │
│─────────────────│─────────│──────────────────────│
│ PK id           │         │ PK id                │
│    name         │         │    name              │
│ FK group_id ────┘         │    org_type          │
│    province     │         │ FK branch_id ────────┘
│    province_code│         │    sub_district      │
│    latitude     │         │    district          │
│    longitude    │         │    province          │
│    admin_name   │         │    email             │
│    contact      │         │    max_participants  │
│                 │         │    gender_male/f/u   │
│                 │         │    contact_name      │
│                 │         │    contact_phone     │
│                 │         │    contact_line_id   │
│                 │         │    enrolled_date     │
│                 │         │    enrolled_until    │
│                 │         └──────────┬───────────┘
│                 │                    │ 1
├────────────────────┐                │
│ 1                  │                │
│      ┌─────────────┴──────┐        │
│      │   participants     │        │
│      │────────────────────│        │
│      │ PK id (SERIAL)     │        │
│      │ FK branch_id ──────┘        │
│      │    prefix          │        │
│      │    first_name      │        │
│      │    last_name       │        │
│      │    gender, age     │        │
│      │    phone, line_id  │        │
│      │    enrolled_date   │        │
│      │    privacy_accepted│        │
│      └─────────┬──────────┘        │
│                │ 1                  │
│ ∞              │ ∞                  │ ∞
├────────────────┴────────────────────┘
│                   records
│───────────────────────────────────────────────
│ PK id (SERIAL)
│    type (individual | bulk)
│ FK branch_id      → branches.id
│ FK org_id         → organizations.id
│ FK participant_id → participants.id
│    name, minutes, date, status
│    morning_male/female/unspecified
│    afternoon_male/female/unspecified
│    evening_male/female/unspecified
│    submitted_by, submitted_phone
└───────────────────────────────────────────────

┌─────────────────┐    ┌──────────────────┐
│   daily_stats   │    │  province_stats   │
│─────────────────│    │──────────────────│
│ PK date         │    │ PK province_code │
│    total_minutes│    │    province      │
│    total_records│    │    total_minutes  │
│    cumulative   │    │    total_records  │
└─────────────────┘    └──────────────────┘
```

## ความสัมพันธ์ (Relationships)

| ความสัมพันธ์ | ประเภท | คำอธิบาย |
|-------------|--------|---------|
| branch_groups → branches | 1:∞ | กลุ่มสาขา (เช่น ภาคกลาง) มีหลายสาขา |
| branches → organizations | 1:∞ (optional) | เฉพาะ ORG-PLJ เชื่อมสาขา, องค์กรภายนอกไม่สังกัดสาขา (branch_id = NULL) |
| branches → participants | 1:∞ | ผู้เข้าร่วมลงทะเบียนผ่านสาขา |
| branches → records | 1:∞ | record ส่งผ่านสาขา |
| organizations → records | 1:∞ | record เป็นขององค์กร |
| participants → records | 1:∞ | record อ้างอิงผู้เข้าร่วม (individual) |

## กฎการนับนาที (Business Rules)

### วิทิสาสมาธิ
- ปฏิบัติสมาธิครั้งละ **5 นาที**
- สูงสุด **3 ครั้ง/วัน** (เช้า กลางวัน เย็น) = **15 นาที/วัน/คน**
- Bulk: จำนวนคน × 5 นาที

### Anti-fraud Limits
| กฎ | ค่า | สถานะ |
|----|-----|-------|
| เพดานต่อครั้ง (individual) | 5 นาที | ✅ ยืนยัน |
| เพดานต่อวัน (individual) | 15 นาที | ✅ ยืนยัน |
| เพดานต่อคน (bulk) | 5 นาที × จำนวนคน | ✅ ยืนยัน |
| Cooldown | ยังไม่ยืนยัน (ปิดไว้) | ⬜ รอหารือ |

### ยอดรวม

```
ยอดรวมทั้งหมด = สถาบันพลังจิตตานุภาพ + องค์กรภายนอก (ไม่ซ้ำกัน)
```

| เงื่อนไข | คำอธิบาย |
|----------|---------|
| `org_id = 'ORG-PLJ'` | นาทีของสถาบันฯ → นับเข้า **รายสาขา** และ **รายกลุ่มสาขา** |
| `org_id ≠ 'ORG-PLJ'` | นาทีขององค์กรภายนอก → **ไม่นับ** เข้ารายสาขา |
| รายจังหวัด | รวม **ทั้งหมด** (สาขา + องค์กร) ในจังหวัดนั้น |
| รายกลุ่มสาขา | เฉพาะ `org_id = 'ORG-PLJ'` |
| รายสาขา | เฉพาะ `org_id = 'ORG-PLJ'` |
| รายองค์กร | ทุกองค์กร (รวม ORG-PLJ) |

## ตารางหลัก

### branch_groups — กลุ่มสาขา
| คอลัมน์ | ชนิด | คำอธิบาย |
|---------|------|---------|
| id | VARCHAR(10) PK | รหัสกลุ่ม เช่น G01 |
| name | VARCHAR(100) | ชื่อกลุ่ม เช่น ภาคกลาง |
| provinces | JSONB | รายการ province_code เช่น ["TH-10","TH-12"] |

### branches — สาขาสถาบันพลังจิตตานุภาพ
| คอลัมน์ | ชนิด | คำอธิบาย |
|---------|------|---------|
| id | VARCHAR(10) PK | รหัสสาขา เช่น B001 |
| name | VARCHAR(200) | ชื่อเต็ม เช่น สถาบันพลังจิตตานุภาพ สาขา 1 กรุงเทพฯ |
| group_id | VARCHAR(10) FK | กลุ่มสาขา → branch_groups.id |
| province | VARCHAR(100) | จังหวัด |
| province_code | VARCHAR(10) | รหัสจังหวัด เช่น TH-10 |
| latitude | DOUBLE | ละติจูด |
| longitude | DOUBLE | ลองจิจูด |
| admin_name | VARCHAR(200) | ชื่อผู้ดูแลสาขา |
| contact | VARCHAR(200) | ข้อมูลติดต่อ |

### organizations — องค์กร
| คอลัมน์ | ชนิด | คำอธิบาย |
|---------|------|---------|
| id | VARCHAR(10) PK | รหัสองค์กร เช่น ORG-PLJ, ORG001 |
| name | VARCHAR(200) | ชื่อองค์กร |
| org_type | VARCHAR(50) | ประเภท: สถาบันพลังจิตตานุภาพ, โรงเรียน, มหาวิทยาลัย, วัด, หน่วยงาน, ชุมชน |
| branch_id | VARCHAR(10) FK | สาขาที่สังกัด → branches.id |
| sub_district | VARCHAR(100) | ตำบล/แขวง |
| district | VARCHAR(100) | อำเภอ/เขต |
| province | VARCHAR(100) | จังหวัด |
| email | VARCHAR(200) | อีเมลองค์กร |
| max_participants | INTEGER | จำนวนผู้เข้าร่วมสูงสุด |
| gender_male | INTEGER | จำนวนเพศชาย |
| gender_female | INTEGER | จำนวนเพศหญิง |
| gender_unspecified | INTEGER | จำนวนไม่ระบุเพศ |
| contact_name | VARCHAR(200) | ชื่อผู้ประสานงาน |
| contact_phone | VARCHAR(50) | เบอร์โทรผู้ประสานงาน |
| contact_line_id | VARCHAR(100) | LINE ID ผู้ประสานงาน |
| enrolled_date | DATE | วันที่สมัคร |
| enrolled_until | DATE | วันที่สิ้นสุดการสมัคร |
| latitude | DOUBLE | ละติจูด |
| longitude | DOUBLE | ลองจิจูด |
| contact | VARCHAR(200) | ข้อมูลติดต่อ (เดิม) |

### participants — ผู้เข้าร่วมรายบุคคล
| คอลัมน์ | ชนิด | คำอธิบาย |
|---------|------|---------|
| id | SERIAL PK | รหัสอัตโนมัติ |
| branch_id | VARCHAR(10) FK | สาขาที่สังกัด → branches.id |
| prefix | VARCHAR(50) | คำนำหน้า |
| first_name | VARCHAR(100) | ชื่อ |
| last_name | VARCHAR(100) | นามสกุล |
| gender | VARCHAR(20) | เพศ: male, female, unspecified |
| age | INTEGER | อายุ |
| sub_district | VARCHAR(100) | ตำบล/แขวง |
| district | VARCHAR(100) | อำเภอ/เขต |
| province | VARCHAR(100) | จังหวัด |
| phone | VARCHAR(50) | เบอร์โทร |
| line_id | VARCHAR(100) | LINE ID |
| enrolled_date | DATE | วันที่ลงทะเบียน |
| privacy_accepted | BOOLEAN | ยอมรับนโยบายข้อมูลส่วนบุคคล |

### records — บันทึกนาทีสมาธิ
| คอลัมน์ | ชนิด | คำอธิบาย |
|---------|------|---------|
| id | SERIAL PK | รหัสอัตโนมัติ |
| type | VARCHAR(20) | individual หรือ bulk |
| branch_id | VARCHAR(10) FK | สาขาที่ส่ง → branches.id |
| org_id | VARCHAR(10) FK | องค์กรเจ้าของนาที → organizations.id |
| participant_id | INTEGER FK | ผู้เข้าร่วม → participants.id |
| name | VARCHAR(200) | ชื่อผู้บันทึก/กลุ่ม |
| minutes | INTEGER | จำนวนนาที (> 0) |
| participant_count | INTEGER | จำนวนผู้เข้าร่วม (bulk) |
| minutes_per_person | INTEGER | นาทีต่อคน (bulk) |
| morning_male | INTEGER | จำนวนชาย รอบเช้า |
| morning_female | INTEGER | จำนวนหญิง รอบเช้า |
| morning_unspecified | INTEGER | จำนวนไม่ระบุ รอบเช้า |
| afternoon_male | INTEGER | จำนวนชาย รอบกลางวัน |
| afternoon_female | INTEGER | จำนวนหญิง รอบกลางวัน |
| afternoon_unspecified | INTEGER | จำนวนไม่ระบุ รอบกลางวัน |
| evening_male | INTEGER | จำนวนชาย รอบเย็น |
| evening_female | INTEGER | จำนวนหญิง รอบเย็น |
| evening_unspecified | INTEGER | จำนวนไม่ระบุ รอบเย็น |
| date | DATE | วันที่ปฏิบัติ |
| submitted_by | VARCHAR(200) | ผู้ส่ง |
| submitted_phone | VARCHAR(50) | เบอร์โทรผู้ส่ง |
| status | VARCHAR(20) | pending → approved / rejected |
| flags | JSONB | ธง anti-fraud |

> **Upsert:** ถ้า `branch_id + org_id + name + date` ซ้ำ → อัพเดตแทนสร้างใหม่

### daily_stats / province_stats — สถิติสรุป (cache)
ตารางสรุปสำหรับ dashboard ไม่มี FK เชื่อมโยง
