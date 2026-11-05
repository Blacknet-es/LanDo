BEGIN;

CREATE TABLE IF NOT EXISTS schema_migrations (
    version VARCHAR(100) PRIMARY KEY,
    applied_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
DO $$
BEGIN
    IF EXISTS (
        SELECT 1 FROM schema_migrations WHERE version = '001_multi_tenant'
    ) THEN
        RAISE EXCEPTION 'Migration 001_multi_tenant has already been applied';
    END IF;
END;
$$;

CREATE EXTENSION IF NOT EXISTS vector;

-- Existing rows have no trustworthy owner and are discarded as requested.
DELETE FROM event_reminders;
DELETE FROM recurrence_rules;
DELETE FROM events;
DELETE FROM user_locations;
DELETE FROM user_settings;

CREATE TABLE users (
    id UUID PRIMARY KEY,
    email VARCHAR(320) NOT NULL,
    hashed_password VARCHAR(255) NOT NULL,
    created_at TIMESTAMPTZ NOT NULL
);
CREATE UNIQUE INDEX ix_users_email ON users (email);

ALTER TABLE user_locations
    ADD COLUMN user_id UUID NOT NULL REFERENCES users(id);
CREATE INDEX ix_user_locations_user_id ON user_locations (user_id);
ALTER TABLE user_locations
    ADD CONSTRAINT uq_user_locations_id_user UNIQUE (id, user_id);

ALTER TABLE events
    DROP CONSTRAINT IF EXISTS events_location_id_fkey;
ALTER TABLE events
    ADD COLUMN user_id UUID NOT NULL REFERENCES users(id);
CREATE INDEX ix_events_user_id ON events (user_id);
ALTER TABLE events
    ADD CONSTRAINT fk_events_location_tenant
    FOREIGN KEY (location_id, user_id)
    REFERENCES user_locations (id, user_id);

ALTER TABLE user_settings
    ADD COLUMN user_id UUID NOT NULL REFERENCES users(id);
CREATE UNIQUE INDEX ix_user_settings_user_id ON user_settings (user_id);

CREATE TABLE location_triggers (
    id UUID PRIMARY KEY,
    user_id UUID NOT NULL REFERENCES users(id),
    location_id VARCHAR NOT NULL,
    trigger_type VARCHAR(32) NOT NULL,
    created_at TIMESTAMPTZ NOT NULL,
    CONSTRAINT fk_location_triggers_location_tenant
        FOREIGN KEY (location_id, user_id)
        REFERENCES user_locations (id, user_id)
);
CREATE INDEX ix_location_triggers_user_id ON location_triggers (user_id);
CREATE INDEX ix_location_triggers_location_id ON location_triggers (location_id);

CREATE TABLE memory_items (
    id UUID PRIMARY KEY,
    user_id UUID NOT NULL REFERENCES users(id),
    content TEXT NOT NULL,
    embedding VECTOR NOT NULL,
    created_at TIMESTAMPTZ NOT NULL
);
CREATE INDEX ix_memory_items_user_id ON memory_items (user_id);

INSERT INTO schema_migrations (version) VALUES ('001_multi_tenant');

COMMIT;
