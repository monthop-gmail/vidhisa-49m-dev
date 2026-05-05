# Branch View API Spec — me-ui

> สถานะ: **ร่าง** — ขอความเห็นทีม backend
>
> Author: ทีม admin-ui · Date: 2026-05-05
>
> ใช้คู่กับ `api-spec.md` (admin-side) — ที่นี่เป็น **public read-only API** สำหรับให้ผู้เข้าร่วมดูยอดของตน

---

## 1. ภาพรวม

โปรเจกต์ใหม่ **me-ui** (sibling ของ admin-ui) — ผู้เข้าร่วมเปิดผ่าน link ที่ admin สาขาส่งใน Line group ของสาขา → ค้นชื่อตัวเอง → ดูยอดสะสมของตน → จำตัวตนใน localStorage ครั้งต่อไปกด link เดิมเข้า dashboard ของตัวเองเลย

### URL format (ตกลงกับทีมแล้ว)

- รูปแบบ: `/br/{branch_id}-{secret}` เช่น `/br/B012-A3F9X2`
- **ดูแล้วรู้ branch ทันที** จาก prefix
- secret = **6 ตัวอักษร** (Crockford base32 alphabet — เพื่อกัน confusion: ไม่มี I, L, O, U)
- alphabet: `0123456789ABCDEFGHJKMNPQRSTVWXYZ` — 32 chars
- combinations: 32⁶ = **~1.07 พันล้านต่อสาขา**

### Trust model (ตกลงกับทีมแล้ว)

| สิ่งที่ป้องกันได้ | สิ่งที่ไม่ป้องกัน |
|---|---|
| คนนอกสาขาเข้าไม่ได้ (ไม่มี secret 6-char) | คนในสาขาเห็นยอดของผู้เข้าร่วมคนอื่นในสาขาเดียวกันได้ — **ยอมรับได้** |
| Brute-force ทำไม่คุ้ม (1.07B/branch + rate limit 30 req/min/IP = 22,800 ปี/สาขา) | Link หลุดทาง Line public → คนทั่วไปเข้าได้ — **ผู้รับผิดชอบ link คือ admin สาขา** |

⚠ **เพราะ secret สั้น 6 chars — Rate limiting เลื่อนเป็น Phase 1 (บังคับ)** ดูข้อ 4

ดังนั้น **ห้ามคืน PII ของผู้เข้าร่วม** (phone, email, line_id, address, age) ใน endpoints public เหล่านี้ — เปิดเฉพาะข้อมูลที่ "เห็นแล้วไม่เสียหาย"

---

## 2. DB Migration

```sql
ALTER TABLE branches
  ADD COLUMN view_secret VARCHAR(6) UNIQUE;

CREATE INDEX idx_branches_view_secret ON branches(view_secret);

-- backfill: generate ของทุกสาขาตอน migrate ครั้งเดียว
-- ใช้ Crockford base32 alphabet (ไม่มี I L O U เพื่อกัน confusion)
DO $$
DECLARE
  alphabet TEXT := '0123456789ABCDEFGHJKMNPQRSTVWXYZ';
  b RECORD;
  s TEXT;
  i INT;
BEGIN
  FOR b IN SELECT id FROM branches WHERE view_secret IS NULL LOOP
    LOOP
      s := '';
      FOR i IN 1..6 LOOP
        s := s || substr(alphabet, 1 + floor(random() * 32)::int, 1);
      END LOOP;
      -- กันชน — ถ้าซ้ำ generate ใหม่
      EXIT WHEN NOT EXISTS (SELECT 1 FROM branches WHERE view_secret = s);
    END LOOP;
    UPDATE branches SET view_secret = s WHERE id = b.id;
  END LOOP;
END $$;

ALTER TABLE branches ALTER COLUMN view_secret SET NOT NULL;

-- เพิ่มคอลัมน์เก็บ Google Form URL ของสาขา (สำหรับให้ผู้เข้าร่วมกรอกบันทึก)
ALTER TABLE branches
  ADD COLUMN record_form_url VARCHAR(500);
-- nullable — สาขาตั้งเองภายหลัง; ไม่บังคับมี
```

**ข้อตกลง view_secret**:
- 6 ตัวอักษร Crockford base32 (`0-9 A-Z` ลบ `I L O U`) — สับสนน้อย, อ่านได้, พิมพ์ใส่มือถือได้
- collision space 32⁶ = ~1.07B → 325 สาขาใช้ 0.00003% ของ space
- **ไม่ regenerate ใน MVP** — link คงที่ตลอดอายุโครงการ (ตามที่ตกลง)
- **ไม่หมดอายุ**

**ข้อตกลง record_form_url**:
- คอลัมน์ใหม่ แยกจาก `ggs_url_*` ที่มีอยู่ (เพื่อกันสับสน — ggs_url คือ sheet URL ที่ระบบใช้ดึง, form_url คือ Form URL ที่ผู้ใช้กรอก)
- branch_admin **แก้ของตัวเองได้** ผ่าน admin-ui หน้า edit branch (ใช้ `PUT /api/branches/{id}` เดิม)
- central_admin เห็น/แก้ของทุกสาขา
- ผู้เข้าร่วมเห็น URL นี้ในหน้า dashboard ของ me-ui เป็นปุ่ม "บันทึกการปฏิบัติ"

---

## 3. Endpoints

ทุก endpoint อยู่ภายใต้ prefix `/api/branch-view/{branch_id}/{secret}/...` — รับ branch_id + secret เป็น **2 path params แยกกัน** เพื่อ:
- API validate ทันทีว่า `secret` ตรงกับ `branch_id` นั้นจริง (กันคนสุ่ม secret ของสาขาอื่น)
- log ดู branch ได้ทันทีไม่ต้อง join

ขอเสนอแยกเป็นไฟล์ใหม่ `services/api/app/routers/branch_view.py` เพื่อไม่ปนกับ admin-side logic

### 3.1 `GET /api/branch-view/{branch_id}/{secret}/info`

**Auth**: ไม่ต้อง — secret เป็น auth ในตัว

**ใช้เมื่อ**: หน้าแรกของ me-ui — verify secret + แสดงชื่อสาขา

**Response 200**:
```json
{
  "branch_id": "B012",
  "branch_name": "บ้านเหมืองหม้อ อ.เมือง จ.แพร่",
  "province": "แพร่"
}
```

**Validation**:
- `branch_id` ต้องมีอยู่ + `secret` ต้องตรงกับ `branches[branch_id].view_secret`
- ใช้ **constant-time compare** (เช่น `secrets.compare_digest`) เพื่อกัน timing attack
- มิฉะนั้น → **404 INVALID_LINK** (ไม่ใช่ 401 — secret หาย/ผิดเป็น "ลิงก์ไม่ถูก" จากมุมมองผู้ใช้)

**Response 404** (secret ไม่ตรงกับ branch_id):
```json
{
  "error": "INVALID_LINK",
  "message": "Link ไม่ถูกต้อง"
}
```

---

### 3.2 `GET /api/branch-view/{branch_id}/{secret}/participants?q=<query>`

**Auth**: secret only

**ใช้เมื่อ**: หน้า search — ผู้ใช้พิมพ์ชื่อตัวเองเพื่อค้นหา

**Query params**:
| name | type | required | note |
|---|---|---|---|
| `q` | string | yes | substring ค้นหาใน first_name / last_name / member_code (case-insensitive) |

**Response 200** (จำกัด 50 รายการต่อ request):
```json
[
  {
    "id": 2,
    "prefix": "นาง",
    "first_name": "กชพร",
    "last_name": "เสนาขันธ์",
    "member_code": "001"
  }
]
```

**ข้อบังคับ**:
- คืนเฉพาะ participants ที่ `status='approved'` ของสาขานี้
- คืน **เฉพาะ field 5 ตัว**: `id`, `prefix`, `first_name`, `last_name`, `member_code`
- **ห้ามคืน**: `phone`, `email`, `line_id`, `age`, `sub_district`, `district`, `province`, `enrolled_date`, `created_at`
- ถ้า `q` ว่าง → คืน array ว่าง `[]` (anti-scrape — ห้าม dump ทั้งสาขา)
- ถ้าเจอ > 50 → คืน 50 ตัวแรกเรียงตามชื่อ (case-insensitive)

---

### 3.3 `GET /api/branch-view/{branch_id}/{secret}/me/{participant_id}`

**Auth**: secret only

**Validation**:
- `branch_id` + `secret` ต้องตรงกัน (เหมือน 3.1, constant-time)
- `participant.branch_id == branch_id` ต้องตรง — มิฉะนั้น **404** (ไม่ใช่ 403 — กันคนเดา id ข้ามสาขา)

**Response 200**:
```json
{
  "id": 2,
  "prefix": "นาง",
  "first_name": "กชพร",
  "last_name": "เสนาขันธ์",
  "member_code": "001",
  "branch_id": "B012",
  "branch_name": "บ้านเหมืองหม้อ อ.เมือง จ.แพร่",

  "profile": {
    "gender": "female",
    "age": 58,
    "sub_district": "เหมืองหม้อ",
    "district": "เมือง",
    "province": "แพร่",
    "phone_masked": "081-xxx-1234",
    "line_id": "@kotchaporn",
    "email": "kodchaporn349@gmail.com",
    "enrolled_date": "2026-04-01",
    "status": "approved"
  },

  "branch_links": {
    "record_form_url": "https://forms.gle/abc123..."
  },

  "stats": {
    "total_minutes": 285,
    "total_records": 19,
    "approved_records": 19,
    "distinct_days": 19
  },

  "daily_minutes": [
    { "date": "2026-04-19", "minutes": 15 },
    { "date": "2026-04-20", "minutes": 15 }
  ],

  "recent_records": [
    {
      "id": 4123,
      "date": "2026-05-02",
      "minutes": 15,
      "status": "approved"
    }
  ]
}
```

**ข้อบังคับ**:
- `daily_minutes` รวม `status='approved'` only, **30 วันล่าสุด** server-side filter
- `recent_records` 10 รายการล่าสุด (ทุก status — ผู้ใช้ดู pending/rejected ของตัวเองได้)
- **ห้ามคืน** field ของ records: `submitted_phone`, `ip_address`, `device_id`, `photo_url`
- `profile.phone_masked` — **mask ฝั่ง API ก่อนส่ง** (format `081-xxx-1234` คงต้น 3 + ท้าย 4) → กัน leak ผ่าน network log/screenshot ที่ลูกหลานเปิด
- `profile.line_id`, `profile.email` — คืนเต็ม (ไม่ sensitive ระดับเดียวกับ phone)
- `branch_links.record_form_url` — `null` ถ้าสาขายังไม่ตั้งค่า → frontend ไม่แสดงปุ่ม

---

### 3.4 `POST /api/branches/{branch_id}/regen-view-secret` (admin only) — *Optional, Phase 4*

**Auth**: `require_central_admin`

**ใช้เมื่อ**: secret หลุด (ไม่ใช่ flow ปกติ)

**Response 200**:
```json
{
  "branch_id": "B012",
  "view_secret": "a7f3e2c8d1b4f9e6...",
  "message": "เปลี่ยน secret สำเร็จ — link เก่าใช้ไม่ได้แล้ว"
}
```

> Phase 4 — ไม่จำเป็นใน MVP; ทำเมื่อมี security incident

---

## 4. Rate Limiting (Phase 1 — **บังคับ**)

⚠ **เพราะ secret 6-char brute-forceable หาก rate ไม่จำกัด** — Phase 1 ต้องทำพร้อมกัน

| Endpoint | Limit | เหตุผล |
|---|---|---|
| `GET /branch-view/{branch_id}/{secret}/info` | **30 req/min/IP** | จุดที่ brute-force มาเช็ค secret ได้เร็วสุด — limit หนัก |
| `GET /branch-view/{branch_id}/{secret}/participants` | 60 req/min/IP + 300 req/min/secret | ใช้งานปกติ ~5 req/min |
| `GET /branch-view/{branch_id}/{secret}/me/{id}` | 120 req/min/IP | ผู้ใช้ refresh page ได้บ่อย |

**คำแนะนำ implementation**:
- ใช้ `slowapi` (in-memory) สำหรับ MVP — ไม่ต้องลง Redis
- key = `f"{request.client.host}:{branch_id}"` (per-IP per-branch)
- **Block 5 นาที** หลัง limit hit (response 429)
- log requests ที่โดน 429 → ดูใน Adminer

**คำนวณความปลอดภัย**:
```
secret combinations:    32^6 = 1,073,741,824
attacker rate limit:    30 req/min = 1,800 req/hr = 43,200/day
worst-case days:        1,073,741,824 / 43,200 ≈ 24,855 days = 68 ปี
```
→ ไม่คุ้มเวลา attacker

---

## 5. Logging (Phase 1 — แนะนำ)

ตรวจ abuse + audit (เพิ่มเป็น Phase 1 เพราะ secret สั้น ต้องรู้ว่ามีคนพยายาม brute-force):

```sql
CREATE TABLE branch_view_log (
  id BIGSERIAL PRIMARY KEY,
  ts TIMESTAMPTZ DEFAULT NOW(),
  branch_id VARCHAR(10),
  ip VARCHAR(45),
  action VARCHAR(20),       -- 'info' | 'search' | 'me' | 'invalid'
  participant_id INT,        -- nullable
  status_code INT,           -- 200, 404, 429
  user_agent VARCHAR(500)
);

CREATE INDEX idx_branch_view_log_ts ON branch_view_log(ts);
CREATE INDEX idx_branch_view_log_branch_ip ON branch_view_log(branch_id, ip);
```

**ใช้งาน**:
- log ทุก request (ใน middleware หรือ dependency)
- เก็บ 30 วัน — auto-purge ผ่าน cron หรือ trigger
- query ผ่าน Adminer ดู IP ที่มี 404 เยอะผิดปกติ → bandit warning

ดูตัวอย่าง alert query:
```sql
-- IP ที่ได้ 404 มากกว่า 100 ครั้งใน 1 ชั่วโมง = น่าจะ brute-force
SELECT ip, branch_id, COUNT(*) AS attempts
FROM branch_view_log
WHERE ts > NOW() - INTERVAL '1 hour' AND status_code = 404
GROUP BY ip, branch_id HAVING COUNT(*) > 100;
```

---

## 6. Tests ที่ต้องครอบ

```python
# services/api/tests/test_branch_view.py

def test_info_with_valid_secret_returns_branch
def test_info_with_invalid_secret_returns_404

def test_participants_search_returns_only_approved
def test_participants_search_excludes_pii_fields    # phone, email, line_id, age
def test_participants_search_empty_q_returns_empty  # anti-scrape
def test_participants_search_limited_to_50
def test_participants_search_case_insensitive

def test_me_returns_own_data_only
def test_me_with_id_from_other_branch_returns_404   # cross-branch isolation
def test_me_excludes_pii_fields                     # phone, ip, device_id, photo_url
def test_me_daily_minutes_only_approved_last_30_days
def test_me_recent_records_includes_all_statuses    # ผู้ใช้เห็น pending ของตัวเองได้

def test_invalid_secret_format_returns_404          # ไม่ใช่ 6-char base32
def test_secret_compare_uses_constant_time          # กัน timing attack
def test_secret_from_other_branch_returns_404       # B012 secret + B044 → 404
def test_rate_limit_kicks_in_after_30_req_per_min   # rate limit
def test_brute_force_attempt_logged                 # logging
```

ทดสอบกับ DB จริงตาม project convention (ห้าม mock)

---

## 7. ผลกระทบกับโค้ดที่มี

✅ **ไม่กระทบ**:
- ❌ ไม่แก้ schema model ที่มีอยู่
- ❌ ไม่แตะ existing endpoints (records, participants, branches)
- ✅ เพิ่ม column 1 ตัว + router file 1 ไฟล์ + migration 1 ตัว
- ✅ ใส่ใน `app/main.py` register router ใหม่

---

## 8. ฝั่ง me-ui — แก้น้อย พร้อม wire ใหม่ทันที

ตอนนี้ใช้ branch_id encoded base64 + hardcoded secret + decode client-side เป็น mockup. เมื่อ API ใหม่พร้อม จะเปลี่ยน 3 ไฟล์:

| ไฟล์ | เปลี่ยน |
|---|---|
| `src/lib/branchKey.ts` | **ลบทิ้ง** — split URL `/br/{branch_id}-{secret}` เป็น 2 ส่วนตรงๆ ไม่ต้อง decode |
| `src/routes/br.$key.tsx` | parse `key = "B012-A3F9X2"` → call `GET /branch-view/B012/A3F9X2/info` ก่อน redirect |
| `src/routes/br.$key.search.tsx` | เปลี่ยน `GET /participants?branch_id=...` → `GET /branch-view/{branch_id}/{secret}/participants?q=...` |
| `src/routes/br.$key.me.$participantId.tsx` | จาก 2 queries → 1 query `GET /branch-view/{branch_id}/{secret}/me/{id}` |

ใช้เวลา ~30 นาทีหลัง API ขึ้น staging

---

## 9. Timeline เสนอ

| Phase | งาน | Owner | เวลา |
|---|---|---|---|
| 1 | Migration + 3 endpoints + **rate limit + logging** + tests + register router | Backend | 2-3 วัน |
| 2 | Swap me-ui ใช้ API จริง | Frontend | 30 นาที |
| 3 | Deploy me-ui as `me.<domain>` หรือ subpath `/me/` | DevOps | ครึ่งวัน |
| 4 | Regen secret endpoint (optional, security incident response) | Backend | 2 ชั่วโมง |

> **เปลี่ยนจาก spec เดิม**: rate limit + logging **ขยับมา Phase 1** เพราะ secret 6-char ต้องการ defense-in-depth จาก brute-force

---

## 10. คำถามขอความเห็นจากทีม backend

1. ใช้ `view_secret VARCHAR(6)` Crockford base32 OK มั้ย? หรืออยากใช้ alphabet อื่น?
2. Path prefix `/api/branch-view/{branch_id}/{secret}/` OK มั้ย? หรืออยากใช้ pattern อื่น?
3. Search บังคับ `q` ไม่ว่าง — OK กับการห้าม dump รึเปล่า?
4. Rate limit ใช้ `slowapi` (in-memory) ได้มั้ย? หรือต้องลง Redis?
5. ตาราง `branch_view_log` แยกจาก main schema OK มั้ย? หรือใช้ external (Loki, etc.)?
6. Migration รัน manually หรือ auto ผ่าน init scripts (`services/db/init/`)?
7. Regen endpoint ใน Phase 4 — ตกลงมั้ย?

นัดคุย 30 นาทีพอ — ตกลง 7 ข้อนี้แล้ว backend เริ่ม implement ได้ทันที

---

## ภาคผนวก — ตัวอย่าง URL จริง

หลัง migration:
```
B012 → secret = "A3F9X2"  (6 chars Crockford base32)
B044 → secret = "K7P2M5"
B047 → secret = "W3T8N4"

User-facing URL (ส่งใน Line group ของสาขา):
https://me.vidhisa49m.com/br/B012-A3F9X2

API calls (ฝั่ง me-ui split branch_id + secret):
GET /api/branch-view/B012/A3F9X2/info
GET /api/branch-view/B012/A3F9X2/participants?q=กชพร
GET /api/branch-view/B012/A3F9X2/me/2
```

**สังเกต**:
- `B012-` prefix → ดูปุ๊บรู้ว่าเป็นสาขาไหน
- `A3F9X2` → secret 6 chars (อ่าน + พิมพ์ในมือถือได้)
- ไม่มี participant_id ใน URL — ผู้รับ link ค้นชื่อตัวเองในหน้า search แล้ว app จำใน localStorage ครั้งต่อไปกด link เดิมไป dashboard เลย

**ลิงก์ที่อ่านได้สบายตา**: เทียบกับ `B012-A3F9X2` (12 chars) vs hex 32-char เดิม `a7f3e2c8d1b4f9e6c5d3a2b1f0e9d8c7` — สั้นกว่า 60%
