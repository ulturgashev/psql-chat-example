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
    name TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- copy paste from the internet. I don't know how does it work.
DO $$
BEGIN
IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'participants_type') THEN 
    CREATE TYPE participants_type AS ENUM (
        'single',
        'group'
    );
END IF;
END $$;

CREATE TABLE IF NOT EXISTS chat.participants (
    user_id TEXT NOT NULL REFERENCES chat.users(id),
    dialog_id TEXT NOT NULL REFERENCES chat.dialogs(id),
    created_at TIMESTAMPTZ NOT NULL,
    type participants_type NOT NULL,
    PRIMARY KEY (user_id, dialog_id)
);

CREATE TABLE IF NOT EXISTS chat.messages (
    idempotency_key_id TEXT PRIMARY KEY,
    dialog_id TEXT NOT NULL REFERENCES chat.dialogs(id),
    from_id TEXT NOT NULL REFERENCES chat.users(id),
    created_at TIMESTAMPTZ NOT NULL,
    unread BOOLEAN DEFAULT true,
    text TEXT,
    media JSON
);

CREATE TABLE IF NOT EXISTS chat.users_mappers (
    id TEXT PRIMARY KEY REFERENCES chat.users(id),
    source_user_id TEXT NOT NULL,
    source_type TEXT NOT NULL
);
