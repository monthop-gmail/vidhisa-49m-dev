-- =============================================
-- Vidhisa 49M — Seed Data (Production)
-- =============================================
-- ข้อมูลจริงมาจาก:
--   - GGS sync (Google Sheet ของแต่ละสาขา)
--   - UI register/record
--   - Enrollment approval
-- =============================================

-- กลุ่มสาขาและสาขาทั้งหมดอยู่ใน 02-branches.sql (325 สาขา, 31 กลุ่ม)
-- PLJ orgs อยู่ใน 03-plj-orgs.sql (auto-create 1 org ต่อ 1 สาขา)

-- Admin กลาง (default password: vidhisa2569 — ต้องเปลี่ยนหลัง deploy)
-- password_hash = bcrypt('vidhisa2569')
INSERT INTO users (username, password_hash, full_name, email, role, status) VALUES
('admin', '$2b$12$AUXoVNCX349/QWTCT/xWlOoPF2rKmQXYNJ3oat5plhNwKRyxxJNwm', 'Admin กลาง', 'admin@vidhisa49m.com', 'central_admin', 'active');
