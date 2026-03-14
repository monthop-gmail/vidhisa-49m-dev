# API Spec — วิทิสา 49 ล้านนาที

> สถานะ: **ร่าง** — รอหารือในที่ประชุม

## หลักการ

- **API-First** — ตกลง contract ก่อน ทีม UI + ทีม API ทำงานคู่ขนานได้
- **REST JSON** — ใช้ง่าย ทุกภาษาเรียกได้
- **ไม่ต้อง Login** (ตามแนวทาง อ.เต้) — เน้นความคล่องตัวกับกลุ่มเป้าหมาย

---

## 1. บันทึกผล (Records)

### POST /api/records — บันทึกยอดนาที

**กรณีองค์กร/โรงเรียน (Bulk)**
```json
{
  "type": "bulk",
  "branch_id": "B001",
  "org_name": "โรงเรียนสาธิต มศว",
  "participant_count": 500,
  "minutes_per_person": 5,
  "total_minutes": 2500,
  "date": "2026-05-15",
  "photo_url": "https://...",
  "submitted_by": "ครูสมใจ"
}
```

**กรณีรายบุคคล (Individual)**
```json
{
  "type": "individual",
  "branch_id": "B001",
  "name": "สมชาย",
  "minutes": 15,
  "date": "2026-05-15"
}
```

**Response: 201 Created**
```json
{
  "id": "R00001",
  "status": "pending",
  "message": "บันทึกสำเร็จ รอสาขาตรวจสอบ"
}
```

**Validation Rules (Anti-fraud):**
- `minutes` ต่อครั้ง: ไม่เกิน 30 นาที (individual)
- `minutes` ต่อวันต่อคน: ไม่เกิน 120 นาที
- `total_minutes` ต่อองค์กร: ไม่เกิน `participant_count × 30`
- Cooldown: ห่างจากครั้งก่อนอย่างน้อย 5 นาที (individual)

> ค่าเพดานทั้งหมดยังเป็น **ร่าง** — รอหารือกับฝ่ายวิชาการ

---

## 2. สถิติ (Stats)

### GET /api/stats/total — ยอดรวมทั้งโครงการ

```json
{
  "total_minutes": 12500000,
  "total_records": 250000,
  "total_branches": 205,
  "total_orgs": 1500,
  "last_updated": "2026-05-15T14:30:00+07:00"
}
```

### GET /api/stats/by-province — ยอดแยกรายจังหวัด

```json
[
  { "province": "กรุงเทพมหานคร", "code": "TH-10", "minutes": 1200000, "records": 25000 },
  { "province": "เชียงใหม่", "code": "TH-50", "minutes": 800000, "records": 18000 },
  ...
]
```

### GET /api/stats/by-branch — ยอดแยกรายสาขา

```json
[
  { "branch_id": "B001", "branch_name": "สาขา 1", "province": "กรุงเทพมหานคร", "minutes": 500000 },
  ...
]
```

### GET /api/stats/daily — ยอดรายวัน (สำหรับกราฟ)

**Query:** `?from=2026-05-01&to=2026-05-15`

```json
[
  { "date": "2026-05-01", "minutes": 380000 },
  { "date": "2026-05-02", "minutes": 420000 },
  ...
]
```

---

## 3. คาดการณ์ (Projection)

### GET /api/projection — ตัวเลขคาดการณ์

```json
{
  "target_minutes": 49000000,
  "current_minutes": 12500000,
  "remaining_minutes": 36500000,
  "deadline": "2026-07-31",
  "days_remaining": 77,
  "daily_rate_current": 400000,
  "daily_rate_needed": 474026,
  "estimated_completion_date": "2026-08-22",
  "on_track": false
}
```

---

## 4. Leaderboard

### GET /api/leaderboard — อันดับสูงสุด

**Query:** `?type=org&limit=10`

```json
[
  { "rank": 1, "name": "โรงเรียนสาธิต มศว", "branch": "สาขา 1", "minutes": 125000 },
  { "rank": 2, "name": "กองกายภาพ ม.เกษตร", "branch": "สาขา 5", "minutes": 98000 },
  ...
]
```

**Query:** `?type=branch&limit=10`

```json
[
  { "rank": 1, "branch_id": "B001", "branch_name": "สาขา 1", "minutes": 2500000 },
  ...
]
```

---

## 5. Live Feed

### GET /api/feed — รายการบันทึกล่าสุด

**Query:** `?limit=20`

```json
[
  {
    "id": "R00500",
    "message": "คุณสมชาย จากสาขา 10 เพิ่งสะสมเพิ่ม 15 นาที",
    "minutes": 15,
    "type": "individual",
    "timestamp": "2026-05-15T14:28:00+07:00"
  },
  {
    "id": "R00499",
    "message": "โรงเรียนอนุบาลฯ ร่วมสะสมยอดรวม 2,500 นาที",
    "minutes": 2500,
    "type": "bulk",
    "timestamp": "2026-05-15T14:25:00+07:00"
  }
]
```

---

## 6. สาขา — ตรวจสอบยอด (Branch Admin)

### GET /api/branch/{branch_id}/pending — รายการรออนุมัติ

```json
[
  {
    "id": "R00450",
    "type": "bulk",
    "org_name": "โรงเรียน...",
    "total_minutes": 2500,
    "date": "2026-05-15",
    "status": "pending",
    "flags": []
  },
  {
    "id": "R00430",
    "type": "individual",
    "name": "...",
    "minutes": 120,
    "date": "2026-05-15",
    "status": "pending",
    "flags": ["daily_limit_reached"]
  }
]
```

### PATCH /api/records/{id}/approve — สาขาอนุมัติ

```json
{ "status": "approved", "approved_by": "ผู้ดูแลสาขา 1" }
```

### PATCH /api/records/{id}/reject — สาขาปฏิเสธ

```json
{ "status": "rejected", "reason": "ยอดไม่ตรงกับหลักฐาน" }
```

---

## Error Response

```json
{
  "error": "DAILY_LIMIT_EXCEEDED",
  "message": "เกินเพดาน 120 นาทีต่อวัน",
  "detail": { "current_today": 110, "attempted": 30, "limit": 120 }
}
```

| Error Code | สาเหตุ |
|-----------|--------|
| `DAILY_LIMIT_EXCEEDED` | เกินเพดานนาทีต่อวัน |
| `SESSION_LIMIT_EXCEEDED` | เกินเพดานนาทีต่อครั้ง |
| `COOLDOWN_ACTIVE` | บันทึกถี่เกินไป รอ cooldown |
| `BULK_LIMIT_EXCEEDED` | ยอดองค์กรเกิน participant × เพดาน |
| `INVALID_BRANCH` | ไม่พบสาขา |
