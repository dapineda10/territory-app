-- Run this once in the Supabase SQL Editor (Database > SQL Editor)
-- Use the service_role key in st.secrets — it bypasses RLS, which is safe
-- for a server-side Streamlit app where the key is never sent to the browser.

CREATE TABLE IF NOT EXISTS users (
    id            BIGSERIAL PRIMARY KEY,
    username      TEXT UNIQUE NOT NULL,
    password_hash TEXT NOT NULL,
    role          TEXT NOT NULL DEFAULT 'user',
    sector        TEXT DEFAULT '',
    created_at    TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS access_windows (
    id         BIGSERIAL PRIMARY KEY,
    user_id    BIGINT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    start_date DATE NOT NULL,
    end_date   DATE NOT NULL,
    note       TEXT DEFAULT '',
    sector     TEXT DEFAULT '',
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS sessions (
    token      TEXT PRIMARY KEY,
    user_id    BIGINT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    expires_at TIMESTAMPTZ NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- One row per zone — upserted on every status change (no unbounded growth)
CREATE TABLE IF NOT EXISTS progreso (
    zona   TEXT PRIMARY KEY,
    estado TEXT NOT NULL,
    fecha  TIMESTAMPTZ DEFAULT NOW()
);
