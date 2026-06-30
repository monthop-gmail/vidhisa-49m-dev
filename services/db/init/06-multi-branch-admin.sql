-- =============================================
-- Multi-branch admin support
-- =============================================
-- ขยายให้ 1 user เป็น admin ของหลายสาขาได้
-- - users.branch_id ยังคงอยู่ (primary branch — backward compat)
-- - users.branch_ids JSONB เป็นรายการสาขาที่ user ดูแล (รวม primary)
-- - backfill จาก branch_id เดิม

ALTER TABLE users
  ADD COLUMN IF NOT EXISTS branch_ids JSONB NOT NULL DEFAULT '[]'::jsonb;

-- backfill: ถ้า branch_ids ว่าง + มี branch_id → ใส่เป็น array [branch_id]
UPDATE users
SET branch_ids = to_jsonb(ARRAY[branch_id])
WHERE branch_id IS NOT NULL
  AND (branch_ids IS NULL OR branch_ids = '[]'::jsonb);

-- index สำหรับ query "user ที่ดูแลสาขา X" (ใช้ contains operator)
CREATE INDEX IF NOT EXISTS idx_users_branch_ids ON users USING GIN (branch_ids);
