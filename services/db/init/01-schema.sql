-- =============================================
-- Vithisa 49M — Database Schema
-- =============================================

CREATE TABLE branch_groups (
    id          VARCHAR(10) PRIMARY KEY,
    name        VARCHAR(100) NOT NULL,
    provinces   JSONB NOT NULL DEFAULT '[]'
);

CREATE TABLE branches (
    id              VARCHAR(10) PRIMARY KEY,
    name            VARCHAR(200) NOT NULL,
    group_id        VARCHAR(10) REFERENCES branch_groups(id),
    province        VARCHAR(100) NOT NULL,
    province_code   VARCHAR(10) NOT NULL,
    latitude        DOUBLE PRECISION,
    longitude       DOUBLE PRECISION,
    admin_name      VARCHAR(200),
    contact         VARCHAR(200),
    created_at      TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE organizations (
    id          VARCHAR(10) PRIMARY KEY,
    name        VARCHAR(200) NOT NULL,
    org_type    VARCHAR(50),
    branch_id   VARCHAR(10) REFERENCES branches(id),
    province    VARCHAR(100),
    latitude    DOUBLE PRECISION,
    longitude   DOUBLE PRECISION,
    contact     VARCHAR(200),
    created_at  TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE records (
    id                  SERIAL PRIMARY KEY,
    type                VARCHAR(20) NOT NULL CHECK (type IN ('individual', 'bulk')),
    branch_id           VARCHAR(10) REFERENCES branches(id),
    name                VARCHAR(200) NOT NULL,
    org_id              VARCHAR(10) REFERENCES organizations(id),
    minutes             INTEGER NOT NULL CHECK (minutes > 0),
    participant_count   INTEGER,
    minutes_per_person  INTEGER,
    date                DATE NOT NULL,
    photo_url           TEXT,
    submitted_by        VARCHAR(200),
    status              VARCHAR(20) NOT NULL DEFAULT 'pending'
                        CHECK (status IN ('pending', 'approved', 'rejected')),
    approved_by         VARCHAR(200),
    flags               JSONB DEFAULT '[]',
    latitude            DOUBLE PRECISION,
    longitude           DOUBLE PRECISION,
    ip_address          VARCHAR(45),
    device_id           VARCHAR(100),
    created_at          TIMESTAMPTZ DEFAULT NOW(),
    updated_at          TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_records_branch_id ON records(branch_id);
CREATE INDEX idx_records_date ON records(date);
CREATE INDEX idx_records_status ON records(status);
CREATE INDEX idx_records_created_at ON records(created_at);

CREATE TABLE daily_stats (
    date                DATE PRIMARY KEY,
    total_minutes       BIGINT DEFAULT 0,
    total_records       INTEGER DEFAULT 0,
    total_branches      INTEGER DEFAULT 0,
    cumulative_minutes  BIGINT DEFAULT 0
);

CREATE TABLE province_stats (
    province_code   VARCHAR(10) PRIMARY KEY,
    province        VARCHAR(100) NOT NULL,
    total_minutes   BIGINT DEFAULT 0,
    total_records   INTEGER DEFAULT 0,
    last_updated    TIMESTAMPTZ DEFAULT NOW()
);
