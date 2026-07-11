# รายงาน Security Audit — ระบบวิทิสา 49 ล้านนาที

- **ขอบเขต:** ทั้งระบบ — API (FastAPI), nginx, Docker Compose, frontend (admin-ui / me-ui)
- **วันที่ตรวจ:** 2026-07-11
- **สถานะ codebase:** working tree สะอาด (ตรวจภาพรวมทั้งโปรเจกต์)
- **ผู้ตรวจ:** Claude Code (Fable 5)

> **หมายเหตุเชิงนโยบาย:** CLAUDE.md ระบุ "ไม่มี Login/Auth ตามแนวทาง อ.เต้" แต่ปัจจุบันระบบ**มี** JWT auth และใช้คุมบาง endpoint จริง (เช่น approve participant, view-link, ggs sync-branch) ส่วนที่เหลือเปิดโล่ง คาดว่าเป็นการเปลี่ยนทิศทางที่ยังทำไม่ครบ ทีมควรตัดสินใจเชิง product ว่าจะบังคับ auth ครอบคลุมแค่ไหน — รายงานนี้ชี้จุดที่ **อย่างน้อยที่สุด** ควรปิด

---

## สรุปผู้บริหาร

| ระดับ | จำนวน | ประเด็นหลัก |
|-------|-------|-------------|
| 🔴 วิกฤต | 2 | PII รั่วผ่าน endpoint ไม่มี auth, แก้ไข/อนุมัติข้อมูลได้โดยไม่ต้อง login |
| 🟠 สูง | 3 | Default secret fallback, CORS เปิดกว้าง, Adminer เปิด port |
| 🟡 กลาง | 4 | ไม่มี token revoke, ไม่เช็คความแข็งแรงรหัสผ่าน, login ไม่มี rate limit, view_secret lockout |

**จุดตายหลัก:** ระบบมี auth อยู่แล้วแต่ endpoint ฝั่ง admin ส่วนใหญ่ไม่ได้เรียกใช้ → PII รั่ว + ปลอมยอด 49 ล้านนาทีได้
**ข้อดีที่ทำได้ดีแล้ว:** SQL parameterized ทั้งหมด (ไม่มี injection), constant-time secret compare, CSP + security headers ครบ, PII masking ฝั่ง me-ui

---

## 🔴 วิกฤต

### C-1. PII รั่วไหลผ่าน endpoint ที่ไม่มี auth

Endpoint อ่านข้อมูลผู้เข้าร่วมเรียกได้โดย**ไม่ต้อง login** และคืน **เบอร์โทรเต็ม, LINE ID, ที่อยู่, เพศ, อายุ** ของผู้เข้าร่วมทุกคนทั้งระบบ

| Endpoint | ไฟล์ | ข้อมูลที่รั่ว |
|----------|------|--------------|
| `GET /api/participants` | `routers/participants.py:26` | รายชื่อ + PII ทั้งหมด (optional auth เท่านั้น) |
| `GET /api/participants/{id}` | `routers/participants.py:484` | PII รายคน |
| `GET /api/participants/export` | `routers/participants.py:68` | **CSV PII ทั้งระบบเป็นไฟล์เดียว** |
| `GET /api/records/export` | `routers/records.py:92` | ข้อมูล record ทั้งหมด |
| `GET /api/branch/{id}/pending` | `routers/branch.py:13` | รายการรอตรวจของสาขา |

**ผลกระทบ:** ละเมิด PDPA โดยตรง — ใครก็ดาวน์โหลด PII ทั้งฐานข้อมูลได้
**ย้อนแย้ง:** me-ui ฝั่ง public อุตส่าห์ mask เบอร์โทร (`branch_view.py:34`) แต่เส้นทาง admin กลับเปิดโล่ง
**แนวทางแก้:** เพิ่ม `Depends(get_current_user)` + `scoped_branch_filter` ให้ทุก endpoint อ่าน PII

### C-2. แก้ไข / อนุมัติข้อมูลได้โดยไม่ต้อง login — ปลอมยอดนาทีได้

Endpoint เขียน/อนุมัติข้อมูลต่อไปนี้เรียกได้จาก internet โดยตรงถ้า deploy:

| Endpoint | ไฟล์ | ความเสี่ยง |
|----------|------|-----------|
| `POST /api/records` | `routers/records.py:226` | สร้าง record ปลอม |
| `PATCH /api/records/{id}/approve` | `routers/records.py:343` | **อนุมัติ record เอง** |
| `PATCH /api/records/{id}/reject` | `routers/records.py:361` | ปฏิเสธ record ของคนอื่น |
| `POST /api/records/import` | `routers/records.py:125` | นำเข้า record จำนวนมาก |
| `POST / PUT /api/participants` | `routers/participants.py:494,537` | สร้าง/แก้ผู้เข้าร่วม |
| `PATCH /api/participants/{id}/transfer` | `routers/participants.py:579` | ย้ายสาขา |
| `POST / PUT /api/organizations` | `routers/organizations.py:257,294` | สร้าง/แก้องค์กร |
| `POST /api/branches`, `POST /api/branches/import` | `routers/branches.py:246,95` | สร้าง/นำเข้าสาขา |
| `POST /api/ggs/sync`, `/ggs/sync-all` | `routers/ggs.py:1038,1002` | trigger sync |

**ผลกระทบ:** คนนอกสร้าง record แล้ว**อนุมัติเอง**ได้ → ทำลายความน่าเชื่อถือของยอดรวมทั้งโครงการ
**แนวทางแก้:** เพิ่ม auth + branch scope ให้ทุก endpoint เขียนข้อมูล (อย่างน้อย create/approve/reject/import)

---

## 🟠 สูง

### H-1. Default secret ถูก hardcode เป็น fallback

- `auth.py:17` — `SECRET_KEY = os.getenv("JWT_SECRET", "vidhisa-49m-secret-change-me")`
- `services/api/compose.yaml` — fallback `JWT_SECRET:-vidhisa-49m-dev-secret`

ถ้าลืมตั้ง `.env` บน production ระบบจะใช้ secret ที่รู้กันทั่วไป → **ใครก็ปลอม JWT เป็น `central_admin` ได้ทันที** ทำให้ auth ทั้งระบบไร้ความหมาย

เพิ่มเติม:
- `POSTGRES_PASSWORD` fallback เป็น `changeme` (`.env.example`, compose หลายไฟล์)
- Seed admin password `vidhisa2569` เป็น plaintext ใน `services/db/init/05-seed.sql:13-15`

**แนวทางแก้:**
- ให้ app **ปฏิเสธการ start** ถ้า `JWT_SECRET` / `POSTGRES_PASSWORD` ไม่ได้ตั้งค่า (แทนการใช้ fallback)
- บังคับเปลี่ยนรหัส admin หลัง deploy ครั้งแรก

### H-2. CORS เปิดกว้างสุด

`main.py:119-124` — `allow_origins=["*"]`, `allow_methods=["*"]`, `allow_headers=["*"]`
รวมกับ JWT ที่เก็บใน `localStorage` (`admin-ui/src/lib/auth.ts:47`) ทำให้เว็บใด ๆ ยิง API ในนามผู้ใช้ได้
**แนวทางแก้:** whitelist origin จริงของ dashboard/admin-ui เท่านั้น

### H-3. Adminer เปิด port สู่ host

`services/adminer/compose.yaml` — เปิด port `8081` เป็นหน้าจัดการ DB เต็มรูปแบบ
ถ้า deploy บนเครื่องที่มี public IP โดยไม่มี firewall จะเข้าถึง DB ได้โดยตรง
**แนวทางแก้:** ผูกกับ `127.0.0.1:8081` เท่านั้น หรือถอด service นี้ออกใน production

---

## 🟡 กลาง

### M-1. JWT ไม่มี logout / revoke
Token อายุ 24 ชม. (`auth.py:19`) เพิกถอนไม่ได้ ถ้าหลุดต้องรอหมดอายุเอง
**แนวทางแก้:** พิจารณา token blacklist หรือลดอายุ + refresh token

### M-2. ไม่เช็คความแข็งแรงของรหัสผ่าน
- `POST /auth/change-password` (`auth.py:61`) — ไม่เช็คความยาว/ความซับซ้อนเลย
- `POST /users/{id}/reset-password` (`enrollments.py:445`) — เช็คแค่ ≥ 6 ตัว
**แนวทางแก้:** กำหนดนโยบายขั้นต่ำ (ความยาว + ไม่ใช้รหัสที่พบบ่อย)

### M-3. `/auth/login` ไม่มี rate limit
มี rate limit เฉพาะ `/branch-view/*` (`branch_view.py`) แต่ login ไม่มี → เสี่ยง brute force รหัสผ่าน
(มี bcrypt ช่วยหน่วงอยู่บ้าง แต่ไม่พอกัน automated attack)
**แนวทางแก้:** ใส่ slowapi limiter ที่ `/auth/login` (เช่น 5–10/นาที ต่อ IP) + lockout เมื่อพลาดหลายครั้ง

### M-4. view_secret ไม่มี lockout ต่อ branch
`view_secret` 6 ตัว Crockford base32 (~10⁹ ค่า) + rate limit 30/min ต่อ IP — brute force ยากพอควรและถือว่ารับได้ แต่ไม่มี lockout ระดับ branch จึงยัง brute force แบบกระจาย IP ได้ในทางทฤษฎี
**แนวทางแก้:** เพิ่ม counter ความพยายามผิดต่อ branch + แจ้งเตือน

---

## ✅ จุดที่ทำได้ดีแล้ว (คงไว้)

- **SQL parameterized ทั้งหมด** — ใช้ SQLAlchemy ORM ไม่มี string interpolation ใน query (ไม่พบ SQL injection)
- **Constant-time compare** — `_verify_secret` ใช้ `secrets.compare_digest` (`branch_view.py:64`) กัน timing attack
- **PII masking ฝั่ง public** — me-ui mask เบอร์โทร, ซ่อน ip/device (`branch_view.py`)
- **Security headers + CSP ครบ** — nginx ตั้ง `X-Content-Type-Options`, `X-Frame-Options`, `Referrer-Policy`, `Permissions-Policy`, CSP ทุก location
- **bcrypt** สำหรับ password hashing
- **Access logging** — บันทึกการเข้าถึง branch-view ทุกครั้ง (`BranchViewLog`)

---

## ลำดับความสำคัญที่แนะนำ

| ลำดับ | รายการ | เหตุผล | ความยากในการแก้ |
|-------|--------|--------|------------------|
| 1 | C-1 + C-2 เพิ่ม auth ให้ endpoint อ่าน/เขียน PII + record | ปิด PII leak + ปลอมยอด (impact สูงสุด) | ปานกลาง — ทำเป็น batch ได้ |
| 2 | H-1 ให้ app fail-fast ถ้าไม่ตั้ง secret | กัน JWT forgery จาก default secret | ต่ำ — เพิ่มไม่กี่บรรทัด |
| 3 | H-3 ปิด Adminer port / bind 127.0.0.1 | ลด attack surface ตรงสู่ DB | ต่ำ |
| 4 | H-2 จำกัด CORS origin | กัน cross-site API abuse | ต่ำ |
| 5 | M-3 rate limit `/auth/login` | กัน brute force | ต่ำ |
| 6 | M-1, M-2, M-4 | เสริมความแข็งแรง | ปานกลาง |

---

*หมายเหตุ: รายงานนี้เป็นการตรวจ static analysis จากซอร์สโค้ด ยังไม่ได้ทดสอบ runtime (penetration test) แนะนำให้ทดสอบยิงจริงบน staging หลังแก้ประเด็นวิกฤต*
