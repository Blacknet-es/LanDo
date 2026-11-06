BEGIN;

CREATE TABLE typologies (
    id VARCHAR PRIMARY KEY,
    name VARCHAR(120) NOT NULL,
    color_hex VARCHAR(7) NOT NULL DEFAULT '#6366f1',
    icon VARCHAR(8) NOT NULL DEFAULT '📌',
    is_system_preset BOOLEAN NOT NULL DEFAULT FALSE,
    created_at TIMESTAMPTZ NOT NULL,
    updated_at TIMESTAMPTZ NOT NULL
);
CREATE INDEX ix_typologies_name ON typologies (name);

CREATE TABLE user_locations (
    id VARCHAR PRIMARY KEY,
    name VARCHAR(120) NOT NULL,
    latitude FLOAT NOT NULL,
    longitude FLOAT NOT NULL,
    radius_meters INTEGER NOT NULL DEFAULT 100,
    created_at TIMESTAMPTZ NOT NULL,
    updated_at TIMESTAMPTZ NOT NULL
);
CREATE INDEX ix_user_locations_name ON user_locations (name);

CREATE TABLE events (
    id VARCHAR PRIMARY KEY,
    title VARCHAR(255) NOT NULL,
    description TEXT,
    start_time TIMESTAMPTZ NOT NULL,
    end_time TIMESTAMPTZ,
    is_all_day BOOLEAN NOT NULL DEFAULT FALSE,
    source VARCHAR(32) NOT NULL DEFAULT 'LOCAL',
    external_id VARCHAR(255),
    is_read_only BOOLEAN NOT NULL DEFAULT FALSE,
    typology_id VARCHAR REFERENCES typologies(id),
    trigger_type VARCHAR(32) NOT NULL DEFAULT 'TIME_BASED',
    location_id VARCHAR REFERENCES user_locations(id),
    trigger_condition VARCHAR(16),
    energy_level VARCHAR(32) NOT NULL DEFAULT 'MEDIUM_ENERGY',
    cognitive_load INTEGER NOT NULL DEFAULT 3,
    dopamine_reward VARCHAR(16) NOT NULL DEFAULT 'MEDIUM',
    created_at TIMESTAMPTZ NOT NULL,
    updated_at TIMESTAMPTZ NOT NULL
);
CREATE INDEX ix_events_title ON events (title);
CREATE INDEX ix_events_start_time ON events (start_time);
CREATE INDEX ix_events_external_id ON events (external_id);
CREATE INDEX ix_events_typology_id ON events (typology_id);
CREATE INDEX ix_events_location_id ON events (location_id);

CREATE TABLE recurrence_rules (
    id VARCHAR PRIMARY KEY,
    event_id VARCHAR NOT NULL UNIQUE REFERENCES events(id) ON DELETE CASCADE,
    frequency VARCHAR(16) NOT NULL,
    interval INTEGER NOT NULL DEFAULT 1,
    until_date TIMESTAMPTZ,
    count INTEGER
);
CREATE INDEX ix_recurrence_rules_event_id ON recurrence_rules (event_id);

CREATE TABLE event_reminders (
    id VARCHAR PRIMARY KEY,
    event_id VARCHAR NOT NULL REFERENCES events(id) ON DELETE CASCADE,
    minutes_before INTEGER NOT NULL,
    is_absorbed_from_external BOOLEAN NOT NULL DEFAULT FALSE,
    status VARCHAR(16) NOT NULL DEFAULT 'PENDING',
    created_at TIMESTAMPTZ NOT NULL
);
CREATE INDEX ix_event_reminders_event_id ON event_reminders (event_id);

CREATE TABLE user_settings (
    id VARCHAR PRIMARY KEY,
    selected_provider VARCHAR NOT NULL DEFAULT 'ollama',
    selected_model VARCHAR NOT NULL DEFAULT 'qwen2.5:7b',
    api_keys JSON NOT NULL,
    ollama_base_url VARCHAR NOT NULL DEFAULT 'http://host.docker.internal:11434',
    created_at TIMESTAMPTZ NOT NULL,
    updated_at TIMESTAMPTZ NOT NULL
);

COMMIT;
