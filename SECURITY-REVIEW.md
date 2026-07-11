# รายงานการตรวจสอบความปลอดภัย — vidhisa-49m-dev

> **โครงการ:** วิทิสา 49 ล้านนาที (ระบบต้นแบบ)
> **วันที่ตรวจ:** 2026-07-11
> **ขอบเขต:** ทั้ง codebase — API (FastAPI), Dashboard (nginx/HTML/JS), Docker Compose, DB schema/seed, me-ui secret handling
> **สถานะ working tree:** สะอาด (ไม่มี pending changes — ตรวจภาพรวมทั้งระบบ)

## สรุปผู้บริหาร (Executive Summary)

พบช่องโหว่ระดับ **วิกฤต 2 รายการ** ที่รวมกันแล้วทำให้ผู้ไม่หวังดีสามารถ **แก้ไข/อนุมัติยอดนาทีของทั้งโครงการได้** ซึ่งกระทบ integrity ของการนับ 49 ล้านนาทีโดยตรง ควรแก้ก่อน deploy สู่ production

| ระดับ | จำนวน | หัวข้อ |
|-------|-------|--------|
| 🔴 วิกฤต | 2 | Endpoint แก้ข้อมูลไม่มี auth, Secret ค่า default hardcode |
| 🟠 สูง | 3 | Stored XSS, CORS `*`, Adminer เปิด port |
| 🟡 กลาง/ต่ำ | 4 | me-ui secret สั้น, SSRF, ไม่มี password policy, JWT ไม่มี revocation |

---

## 🔴 วิกฤต

### 1. Endpoint ที่แก้ไขข้อมูลสำคัญจำนวนมากไม่มีการตรวจสอบสิทธิ์ (Broken Access Control)

**ความรุนแรง:** วิกฤต
**ตำแหน่ง:** `services/api/app/routers/` หลายไฟล์

โมเดล authorization ไม่สอดคล้องกัน — บาง endpoint ใส่ JWT (`get_current_user` / `require_central_admin`) แต่หลาย endpoint ที่แก้ข้อมูลสำคัญเปิดโล่ง เรียกได้โดยไม่ต้อง login

| Endpoint | ไฟล์:บรรทัด | ความเสี่ยง |
|----------|-------------|------------|
| `PATCH /records/{id}/approve` | `records.py:343` | **ใครก็อนุมัตินาทีได้** — ทำลาย integrity การนับ |
| `PATCH /records/{id}/reject` | `records.py:361` | **ใครก็ปฏิเสธนาทีได้** |
| `POST /records` | `records.py:226` | สร้าง record ปลอม |
| `POST/PUT /participants` | `participants.py:494,537` | สร้าง/แก้ผู้เข้าร่วม |
| `PATCH /participants/{id}/transfer` | `participants.py:579` | ย้ายผู้เข้าร่วมข้ามสาขา |
| `POST /branches` | `branches.py:246` | สร้างสาขา |
| `POST /organizations`, `PUT /organizations/{id}` | `organizations.py:257,294` | สร้าง/แก้องค์กร |
| `POST /*/import` | branches/orgs/participants/records | bulk import ไม่ต้อง auth |

**ผลกระทบ:** ผู้ไม่หวังดีที่เข้าถึง API ได้ (โดยเฉพาะเมื่อ CORS = `*`, ดูข้อ 4) สามารถปลอม/อนุมัติ/ลบยอดนาทีของทั้งโครงการได้ ซึ่งเป็นหัวใจของระบบ

**หมายเหตุเชิงนโยบาย:** `CLAUDE.md` ระบุ "ไม่มี Login/Auth ตามแนวทาง อ.เต้" แต่โค้ดจริงมี JWT + role อยู่แล้วบางส่วน จึงเกิดความไม่สอดคล้อง **ต้องให้ทีม/อ.เต้ ตัดสินใจให้ชัด** ว่าจะป้องกัน mutation endpoint หรือไม่

**คำแนะนำ:** เพิ่ม dependency `Depends(get_current_user)` (หรือ `require_central_admin`) ให้ทุก endpoint ที่แก้ข้อมูล โดยเริ่มจาก records approve/reject ก่อน เพราะกระทบการนับโดยตรง

---

### 2. Secret ค่า default ถูก hardcode และเปิดเผยในซอร์สโค้ด

**ความรุนแรง:** วิกฤต

| รายการ | ตำแหน่ง | ปัญหา |
|--------|---------|-------|
| `JWT_SECRET` fallback | `auth.py:17` = `"vidhisa-49m-secret-change-me"` | ถ้า deploy โดยไม่ตั้ง env → **ปลอม JWT เป็น `central_admin` ได้ทันที** (HS256 + secret ที่รู้กันทั้งโลก) = คุมทั้งระบบ |
| รหัส admin default | `db/init/05-seed.sql:13-16` = `vidhisa2569` | เขียนไว้ใน comment + อยู่ใน repo |
| `POSTGRES_PASSWORD` default | `.env.example:6`, `config.py:12` = `changeme` | รหัส DB คาดเดาได้ |

**ผลกระทบ:** การรู้ `JWT_SECRET` ค่า default ทำให้ปลอม token สิทธิ์สูงสุดได้ → bypass ทุกการป้องกัน (รวมถึงข้อ 1 หากแก้แล้ว)

**คำแนะนำ:**
- ทำ **fail-closed**: ให้แอปปฏิเสธการ start ถ้า `JWT_SECRET` ยังเป็นค่า default หรือว่าง
- บังคับเปลี่ยนรหัส admin ในการ login ครั้งแรก
- ลบรหัสจริงออกจาก comment ในซอร์ส, บังคับตั้ง `POSTGRES_PASSWORD` ผ่าน env เท่านั้น

---

## 🟠 สูง

### 3. Stored XSS ใน Admin Dashboard

**ความรุนแรง:** สูง
**ตำแหน่ง:** `services/dashboard/html/js/admin.js`, `feed.js`

โค้ดใช้ `innerHTML` ต่อ string โดยตรงกับข้อมูลผู้ใช้ที่ไม่ได้ escape เช่น:
- `admin.js:70-71` — `${p.prefix}${p.first_name} ${p.last_name}`
- `admin.js:28` — `${org.name}`

ชื่อเหล่านี้มาจาก `POST /participants` ที่ **เปิดไม่มี auth (ข้อ 1)** → ผู้โจมตีลงทะเบียนชื่อที่ฝัง payload เช่น `<img src=x onerror=...>` แล้วสคริปต์รันในเบราว์เซอร์ของ admin เมื่อเปิดดูรายการ (Stored XSS)

**ตัวขยายความเสี่ยง:** CSP ตั้ง `script-src 'self' 'unsafe-inline'` (`nginx.conf:13`) — `'unsafe-inline'` ทำให้ CSP กัน inline script XSS **ไม่ได้เลย**

**คำแนะนำ:**
- เพิ่มฟังก์ชัน `escapeHtml()` และใช้กับทุกค่าที่มาจากผู้ใช้ก่อน interpolate เข้า `innerHTML` (หรือใช้ `textContent`)
- พิจารณาถอด `'unsafe-inline'` ออกจาก `script-src` (ต้อง refactor inline handler เป็น external ก่อน)

### 4. CORS อนุญาตทุก origin (`allow_origins=["*"]`)

**ความรุนแรง:** สูง
**ตำแหน่ง:** `services/api/app/main.py:121`

รวมกับ mutating endpoint ที่ไม่มี auth (ข้อ 1) ทำให้เว็บไซต์ใดก็ได้สั่งเบราว์เซอร์ของผู้ใช้ยิง API เพื่อแก้ข้อมูลได้ (ลักษณะคล้าย CSRF)

**คำแนะนำ:** จำกัด `allow_origins` เป็น origin ของ dashboard จริงเท่านั้น

### 5. Adminer เปิด port 8081 สู่ภายนอก

**ความรุนแรง:** สูง (ขึ้นกับการ deploy)
**ตำแหน่ง:** `services/adminer/compose.yaml`

Web UI จัดการฐานข้อมูลโดยตรง หาก host expose port นี้ออกอินเทอร์เน็ต + รหัส DB เป็น `changeme` (ข้อ 2) → เข้าถึง/แก้ไขฐานข้อมูลทั้งหมดได้

**คำแนะนำ:** ไม่ publish port ออกภายนอกบน production (เข้าผ่าน internal network / SSH tunnel เท่านั้น) หรือไม่รัน service นี้บน prod

---

## 🟡 กลาง / ต่ำ

### 6. me-ui view secret สั้น (กลาง)
`branch_view.py:29-31` — secret 6 ตัว Crockford base32 (~32⁶ ≈ 10⁹) มี rate limit 30/นาที การ brute-force ทั้ง space ใช้เวลานานมากในทางปฏิบัติ และ participant_id เป็น sequential (เดาได้) แต่ scoped ต่อ branch + secret แล้ว และ PII ถูก mask → **ยอมรับได้** สำหรับ read-only แต่แนะนำเพิ่มความยาว secret เป็น 8-10 ตัวเพื่อความมั่นใจ

### 7. SSRF ที่ GGS sync (ต่ำ)
`ggs.py` — จำกัดเฉพาะ Google Sheets domain ผ่าน `extract_sheet_id` regex แต่ `follow_redirects=True` (`ggs.py:105,124`) เปิดช่องเล็กน้อย ความเสี่ยงต่ำเพราะ path ถูกจำกัด

### 8. ไม่มี Password Policy (ต่ำ)
`auth.py` / `enrollments.py:445` — `change-password` และ `reset-password` ไม่ตรวจความยาว/ความซับซ้อนของรหัสใหม่ ตั้งรหัสสั้นได้

### 9. JWT ไม่มี revocation (ต่ำ)
`auth.py:19` — token อายุ 24 ชม. ไม่มีกลไกเพิกถอน หาก token รั่วใช้ได้จนหมดอายุ

---

## ✅ จุดที่ทำได้ดีแล้ว

- Security headers ครบทุก location ใน `nginx.conf` (X-Content-Type-Options, X-Frame-Options, Referrer-Policy, Permissions-Policy, CSP)
- SQL ใช้ SQLAlchemy ORM แบบ parameterized ทั้งหมด — **ไม่พบ raw SQL f-string** (ไม่มี SQL injection)
- `branch_view.py` ออกแบบดี: `compare_digest` (constant-time), regex validate secret, rate limit, PII masking (`_mask_phone`), audit log ทุก request
- Password ใช้ bcrypt (`passlib`)
- `scoped_branch_filter` / `check_branch_access` กัน cross-branch access ได้ดีสำหรับ endpoint ที่มี auth

---

## ลำดับการดำเนินการที่แนะนำ

1. **[วิกฤต]** เพิ่ม auth ให้ mutating endpoint — เริ่มจาก `records approve/reject` (ข้อ 1)
2. **[วิกฤต]** Fail-closed เมื่อ `JWT_SECRET` เป็นค่า default + บังคับเปลี่ยนรหัส admin ครั้งแรก (ข้อ 2)
3. **[สูง]** เพิ่ม `escapeHtml()` ใน dashboard JS (ข้อ 3)
4. **[สูง]** จำกัด CORS origin (ข้อ 4) + ปิด Adminer port บน prod (ข้อ 5)
5. **[กลาง/ต่ำ]** ทยอยแก้ข้อ 6-9

> **หมายเหตุ:** การเพิ่ม auth (ข้อ 1) อาจกระทบ integration test (139 เคส) และขัดกับแนวทาง "ไม่มี auth" ของ อ.เต้ — **ควรยืนยันนโยบายกับทีมก่อนลงมือ**
