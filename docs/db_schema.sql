-- eng_cards DB schema (PostgreSQL)
-- MVP: single target language (ru), single source language (en)

CREATE EXTENSION IF NOT EXISTS "pgcrypto"; -- for gen_random_uuid()

CREATE TABLE users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    google_id VARCHAR(64) UNIQUE NOT NULL,
    email VARCHAR(255) UNIQUE NOT NULL,
    name VARCHAR(255),
    avatar_url VARCHAR(512),
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE topics (
    id SERIAL PRIMARY KEY,
    slug VARCHAR(64) UNIQUE NOT NULL,   -- 'food', 'travel', 'work'
    name_en VARCHAR(100) NOT NULL,
    name_ru VARCHAR(100) NOT NULL
);

-- Shared dictionary. One row per unique English word/phrase, cached
-- from MyMemory (translation) + Free Dictionary API (transcription/examples).
CREATE TABLE words (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    text VARCHAR(255) NOT NULL,              -- normalized lowercase
    translation VARCHAR(255) NOT NULL,       -- ru
    transcription VARCHAR(255),              -- IPA, nullable if lookup failed
    part_of_speech VARCHAR(32),
    examples JSONB NOT NULL DEFAULT '[]',    -- ["I had an apple for lunch.", ...]
    audio_url VARCHAR(512),
    cefr_level VARCHAR(2),                   -- A1..C2, nullable for user-added words
    topic_id INT REFERENCES topics(id),
    source VARCHAR(16) NOT NULL DEFAULT 'user_added', -- 'seed' | 'user_added'
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (text)
);
CREATE INDEX idx_words_topic ON words(topic_id);
CREATE INDEX idx_words_level ON words(cefr_level);

-- Which words a user has in their personal deck.
CREATE TABLE user_words (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    word_id UUID NOT NULL REFERENCES words(id) ON DELETE CASCADE,
    source VARCHAR(16) NOT NULL DEFAULT 'manual', -- 'manual' | 'suggested'
    added_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (user_id, word_id)
);
CREATE INDEX idx_user_words_user ON user_words(user_id);

-- 1:1 with user_words. FSRS algorithm state.
CREATE TABLE fsrs_states (
    user_word_id UUID PRIMARY KEY REFERENCES user_words(id) ON DELETE CASCADE,
    state VARCHAR(16) NOT NULL DEFAULT 'new', -- new|learning|review|relearning
    step SMALLINT,                            -- fsrs learning/relearning micro-step, null once in review
    stability FLOAT,
    difficulty FLOAT,
    due_date TIMESTAMPTZ NOT NULL DEFAULT now(),
    reps INT NOT NULL DEFAULT 0,
    lapses INT NOT NULL DEFAULT 0,
    last_review TIMESTAMPTZ
);
CREATE INDEX idx_fsrs_due ON fsrs_states(due_date);

-- Every review event, across all activity types. Used for stats and
-- as raw data if we ever want to personalize FSRS parameters per user.
CREATE TABLE review_logs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_word_id UUID NOT NULL REFERENCES user_words(id) ON DELETE CASCADE,
    activity_type VARCHAR(16) NOT NULL, -- 'flip' | 'multiple_choice' | 'recall'
    rating SMALLINT NOT NULL,           -- 1=Again 2=Hard 3=Good 4=Easy
    elapsed_days FLOAT,                 -- days since previous review, for FSRS
    reviewed_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX idx_review_logs_user_word ON review_logs(user_word_id);
