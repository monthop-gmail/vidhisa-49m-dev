-- =============================================
-- Vidhisa 49M — Database Schema
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
    custom_region   VARCHAR(100),
    sub_district    VARCHAR(100),
    district        VARCHAR(100),
    province        VARCHAR(100) NOT NULL,
    province_code   VARCHAR(10) NOT NULL,
    latitude        DOUBLE PRECISION,
    longitude       DOUBLE PRECISION,
    admin_name      VARCHAR(200),
    contact         VARCHAR(200),
    opening_hours   VARCHAR(500),
    created_at      TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE organizations (
    id                  VARCHAR(10) PRIMARY KEY,
    name                VARCHAR(200) NOT NULL,
    org_type            VARCHAR(50),
    branch_id           VARCHAR(10) REFERENCES branches(id),
    sub_district        VARCHAR(100),
    district            VARCHAR(100),
    province            VARCHAR(100),
    email               VARCHAR(200),
    max_participants    INTEGER,
    gender_male         INTEGER DEFAULT 0,
    gender_female       INTEGER DEFAULT 0,
    gender_unspecified  INTEGER DEFAULT 0,
    contact_name        VARCHAR(200),
    contact_phone       VARCHAR(50),
    contact_line_id     VARCHAR(100),
    enrolled_date       DATE,
    enrolled_until      DATE,
    latitude            DOUBLE PRECISION,
    longitude           DOUBLE PRECISION,
    contact             VARCHAR(200),
    created_at          TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE participants (
    id                  SERIAL PRIMARY KEY,
    branch_id           VARCHAR(10) REFERENCES branches(id),
    prefix              VARCHAR(50),
    first_name          VARCHAR(100) NOT NULL,
    last_name           VARCHAR(100) NOT NULL,
    gender              VARCHAR(20),
    age                 INTEGER,
    sub_district        VARCHAR(100),
    district            VARCHAR(100),
    province            VARCHAR(100),
    phone               VARCHAR(50),
    line_id             VARCHAR(100),
    enrolled_date       DATE,
    privacy_accepted    BOOLEAN DEFAULT FALSE,
    created_at          TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_participants_branch_id ON participants(branch_id);

CREATE TABLE records (
    id                  SERIAL PRIMARY KEY,
    type                VARCHAR(20) NOT NULL CHECK (type IN ('individual', 'bulk')),
    branch_id           VARCHAR(10) REFERENCES branches(id),
    name                VARCHAR(200) NOT NULL,
    org_id              VARCHAR(10) REFERENCES organizations(id),
    participant_id      INTEGER REFERENCES participants(id),
    minutes             INTEGER NOT NULL CHECK (minutes > 0),
    participant_count   INTEGER,
    minutes_per_person  INTEGER,
    morning_male        INTEGER DEFAULT 0,
    morning_female      INTEGER DEFAULT 0,
    morning_unspecified INTEGER DEFAULT 0,
    afternoon_male      INTEGER DEFAULT 0,
    afternoon_female    INTEGER DEFAULT 0,
    afternoon_unspecified INTEGER DEFAULT 0,
    evening_male        INTEGER DEFAULT 0,
    evening_female      INTEGER DEFAULT 0,
    evening_unspecified INTEGER DEFAULT 0,
    date                DATE NOT NULL,
    photo_url           TEXT,
    submitted_by        VARCHAR(200),
    submitted_phone     VARCHAR(50),
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
