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
┌────────┴────────┐         ┌──────────────────┐
│    branches     │ 1     ∞ │  organizations   │
│─────────────────│─────────│──────────────────│
│ PK id           │         │ PK id            │
│    name         │         │    name          │
│ FK group_id ────┘         │    org_type      │
│    province     │         │ FK branch_id ────┘
│    province_code│         │    province      │
│    latitude     │         │    latitude      │
│    longitude    │         │    longitude     │
│    admin_name   │         │    contact       │
│    contact      │         └────────┬─────────┘
└────────┬────────┘                  │ 1
         │ 1                         │
         │                           │
         │ ∞                         │ ∞
┌────────┴───────────────────────────┴─────────┐
│                   records                     │
│───────────────────────────────────────────────│
│ PK id (SERIAL)                                │
│    type (individual | bulk)                   │
│ FK branch_id  → branches.id                   │
│ FK org_id     → organizations.id              │
│    name, minutes, date, status ...            │
└───────────────────────────────────────────────┘

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
| branches → records | 1:∞ | record ส่งผ่านสาขา |
| organizations → records | 1:∞ | record เป็นขององค์กร |

## กฎการนับนาที (Business Rules)

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
| province | VARCHAR(100) | จังหวัด |
| latitude | DOUBLE | ละติจูด |
| longitude | DOUBLE | ลองจิจูด |
| contact | VARCHAR(200) | ข้อมูลติดต่อ |

### records — บันทึกนาทีสมาธิ
| คอลัมน์ | ชนิด | คำอธิบาย |
|---------|------|---------|
| id | SERIAL PK | รหัสอัตโนมัติ |
| type | VARCHAR(20) | individual หรือ bulk |
| branch_id | VARCHAR(10) FK | สาขาที่ส่ง → branches.id |
| org_id | VARCHAR(10) FK | องค์กรเจ้าของนาที → organizations.id |
| name | VARCHAR(200) | ชื่อผู้บันทึก/กลุ่ม |
| minutes | INTEGER | จำนวนนาที (> 0) |
| participant_count | INTEGER | จำนวนผู้เข้าร่วม (bulk) |
| minutes_per_person | INTEGER | นาทีต่อคน (bulk) |
| date | DATE | วันที่ปฏิบัติ |
| status | VARCHAR(20) | pending → approved / rejected |
| flags | JSONB | ธง anti-fraud |

### daily_stats / province_stats — สถิติสรุป (cache)
ตารางสรุปสำหรับ dashboard ไม่มี FK เชื่อมโยง
