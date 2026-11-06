BEGIN;

ALTER TABLE users
    ADD COLUMN preferred_language VARCHAR(5) NOT NULL DEFAULT 'es',
    ADD CONSTRAINT ck_users_preferred_language CHECK (preferred_language IN ('es', 'en'));

CREATE TABLE event_outbox (
    id UUID PRIMARY KEY,
    event_id UUID NOT NULL UNIQUE,
    user_id UUID NOT NULL REFERENCES users(id),
    event_type VARCHAR(100) NOT NULL,
    payload JSONB NOT NULL,
    attempts INTEGER NOT NULL DEFAULT 0,
    next_attempt_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    delivered_at TIMESTAMPTZ,
    last_error TEXT
);
CREATE INDEX ix_event_outbox_event_id ON event_outbox (event_id);
CREATE INDEX ix_event_outbox_user_id ON event_outbox (user_id);
CREATE INDEX ix_event_outbox_event_type ON event_outbox (event_type);
CREATE INDEX ix_event_outbox_next_attempt_at ON event_outbox (next_attempt_at);

COMMIT;
