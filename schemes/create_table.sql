CREATE SCHEMA IF NOT EXISTS chat;

CREATE TABLE IF NOT EXISTS chat.users (
    id TEXT PRIMARY KEY,
    created_at TIMESTAMPTZ NOT NULL,
    username TEXT NOT NULL,
    first_name TEXT,
    language_code TEXT
);

CREATE TABLE IF NOT EXISTS chat.dialogs (
    id TEXT PRIMARY KEY,
    created_at TIMESTAMPTZ NOT NULL,
    user_sender TEXT NOT NULL REFERENCES chat.users(id),
    user_receiver TEXT NOT NULL REFERENCES chat.users(id) CHECK (user_sender <> user_receiver),
    UNIQUE (user_sender, user_receiver)
);

-- TODO: add to check user_id in dialogs
CREATE TABLE IF NOT EXISTS chat.unread_counters (
    id TEXT PRIMARY KEY,
    dialog_id TEXT NOT NULL REFERENCES chat.dialogs(id),
    user_id TEXT NOT NULL REFERENCES chat.users(id),
    counter INT DEFAULT 0
);

-- NOTE: may be it more scalable
-- CREATE TABLE IF NOT EXISTS chat.counters (
--     id TEXT PRIMARY KEY REFERENCES chat.dialogs(id),
--     counter INT DEFAULT 0
-- )

CREATE TABLE IF NOT EXISTS chat.messages (
    idempotency_key_id TEXT PRIMARY KEY,
    dialog_id TEXT NOT NULL REFERENCES chat.dialogs(id),
    id BIGINT NOT NULL,
    from_id TEXT NOT NULL REFERENCES chat.users(id),
    created_at TIMESTAMPTZ NOT NULL,
    unread BOOLEAN DEFAULT true,
    text TEXT,
    media JSON,
    UNIQUE (dialog_id, id)
);

CREATE TABLE IF NOT EXISTS chat.users_mappers (
    id TEXT PRIMARY KEY REFERENCES chat.users(id),
    source_user_id TEXT NOT NULL,
    source_type TEXT NOT NULL
);
