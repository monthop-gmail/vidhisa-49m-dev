-- =============================================
-- Sync Logs — audit trail สำหรับ GGS sync
-- =============================================

CREATE TABLE IF NOT EXISTS sync_logs (
    id                    BIGSERIAL PRIMARY KEY,
    branch_id             VARCHAR(10),          -- NULL = sync-all (batch)
    sync_type             VARCHAR(20) NOT NULL, -- record_ind | record_bulk | org | sync_all
    started_at            TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    finished_at           TIMESTAMPTZ,
    status                VARCHAR(10) NOT NULL DEFAULT 'ok'
                          CHECK (status IN ('ok', 'error', 'partial')),
    created               INTEGER DEFAULT 0,
    updated               INTEGER DEFAULT 0,
    participants_created  INTEGER DEFAULT 0,
    error_count           INTEGER DEFAULT 0,
    errors                JSONB,                -- ["แถว 513: ...", ...]
    message               TEXT,                 -- summary/error message
    triggered_by          VARCHAR(20) DEFAULT 'auto'
                          CHECK (triggered_by IN ('auto', 'manual', 'admin'))
);

CREATE INDEX IF NOT EXISTS idx_sync_logs_branch_finished
    ON sync_logs(branch_id, finished_at DESC);
CREATE INDEX IF NOT EXISTS idx_sync_logs_finished
    ON sync_logs(finished_at DESC);
CREATE INDEX IF NOT EXISTS idx_sync_logs_status
    ON sync_logs(status) WHERE status != 'ok';
