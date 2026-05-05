-- =============================================
-- Branch View — public read-only API for participants (me-ui)
-- =============================================
-- รัน "หลัง" 02-branches.sql เพื่อให้ branches table มีอยู่แล้ว
-- - เพิ่ม view_secret + record_form_url ที่ branches
-- - backfill view_secret ของทุกสาขาด้วย Crockford base32 6 chars
-- - สร้าง branch_view_log table

ALTER TABLE branches
  ADD COLUMN IF NOT EXISTS view_secret VARCHAR(6),
  ADD COLUMN IF NOT EXISTS record_form_url VARCHAR(500);

DO $$
DECLARE
  alphabet TEXT := '0123456789ABCDEFGHJKMNPQRSTVWXYZ';  -- Crockford (no I L O U)
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
      EXIT WHEN NOT EXISTS (SELECT 1 FROM branches WHERE view_secret = s);
    END LOOP;
    UPDATE branches SET view_secret = s WHERE id = b.id;
  END LOOP;
END $$;

CREATE UNIQUE INDEX IF NOT EXISTS idx_branches_view_secret ON branches(view_secret);
ALTER TABLE branches ALTER COLUMN view_secret SET NOT NULL;

CREATE TABLE IF NOT EXISTS branch_view_log (
  id BIGSERIAL PRIMARY KEY,
  ts TIMESTAMPTZ DEFAULT NOW(),
  branch_id VARCHAR(10),
  ip VARCHAR(45),
  action VARCHAR(20),
  participant_id INT,
  status_code INT,
  user_agent VARCHAR(500)
);

CREATE INDEX IF NOT EXISTS idx_branch_view_log_ts ON branch_view_log(ts);
CREATE INDEX IF NOT EXISTS idx_branch_view_log_branch_ip ON branch_view_log(branch_id, ip);
