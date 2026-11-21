-- Gacha MVP-1. Independent game namespace; never touch Velvet/Dominus/Demian databases.
-- Apply in an empty dedicated PostgreSQL database. No production seed, players or secrets.
BEGIN;
CREATE SCHEMA IF NOT EXISTS gacha;

CREATE TABLE IF NOT EXISTS gacha.players (
    id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    telegram_user_id bigint NOT NULL UNIQUE CHECK (telegram_user_id > 0),
    is_blocked boolean NOT NULL DEFAULT false,
    created_at timestamptz NOT NULL DEFAULT now()
);

-- The player's daily bucket is REPLACED with ten at midnight Europe/Moscow.
-- A newer game day may never be overwritten by an older request.
CREATE TABLE IF NOT EXISTS gacha.daily_attempts (
    player_id bigint PRIMARY KEY REFERENCES gacha.players(id) ON DELETE RESTRICT,
    game_day date NOT NULL,
    remaining smallint NOT NULL CHECK (remaining BETWEEN 0 AND 10),
    updated_at timestamptz NOT NULL DEFAULT now()
);
CREATE TABLE IF NOT EXISTS gacha.daily_grant_audit (
    player_id bigint NOT NULL REFERENCES gacha.players(id) ON DELETE RESTRICT,
    game_day date NOT NULL,
    amount smallint NOT NULL CHECK (amount = 10),
    created_at timestamptz NOT NULL DEFAULT now(),
    PRIMARY KEY (player_id, game_day)
);
CREATE TABLE IF NOT EXISTS gacha.bonus_attempts (
    player_id bigint PRIMARY KEY REFERENCES gacha.players(id) ON DELETE RESTRICT,
    remaining bigint NOT NULL DEFAULT 0 CHECK (remaining >= 0),
    updated_at timestamptz NOT NULL DEFAULT now()
);
CREATE TABLE IF NOT EXISTS gacha.bonus_grants (
    request_id uuid PRIMARY KEY,
    player_id bigint NOT NULL REFERENCES gacha.players(id) ON DELETE RESTRICT,
    amount integer NOT NULL CHECK (amount > 0),
    reason text NOT NULL CHECK (length(trim(reason)) BETWEEN 1 AND 300),
    granted_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS gacha.wallets (
    player_id bigint PRIMARY KEY REFERENCES gacha.players(id) ON DELETE RESTRICT,
    balance bigint NOT NULL DEFAULT 0 CHECK (balance >= 0)
);
CREATE TABLE IF NOT EXISTS gacha.wallet_ledger (
    event_id uuid PRIMARY KEY,
    player_id bigint NOT NULL REFERENCES gacha.players(id) ON DELETE RESTRICT,
    delta bigint NOT NULL CHECK (delta <> 0),
    balance_after bigint NOT NULL CHECK (balance_after >= 0),
    reason text NOT NULL CHECK (length(trim(reason)) BETWEEN 1 AND 300),
    created_at timestamptz NOT NULL DEFAULT now()
);

-- Art is never pre-populated. One approved card per rarity + an event/advent
-- card may be imported later, only after exact originals are verified.
CREATE TABLE IF NOT EXISTS gacha.cards (
    card_id text PRIMARY KEY CHECK (card_id ~ '^[a-z0-9][a-z0-9_-]{0,63}$'),
    kind text NOT NULL CHECK (kind IN ('standard', 'event')),
    rarity text,
    title text NOT NULL CHECK (length(trim(title)) BETWEEN 1 AND 200),
    drop_key text NOT NULL DEFAULT 'main' CHECK (drop_key ~ '^[a-z0-9_-]{1,40}$'),
    media_asset_ref text,
    is_active boolean NOT NULL DEFAULT false,
    created_at timestamptz NOT NULL DEFAULT now(),
    CHECK ((kind = 'standard' AND rarity IN ('Classic','Elite','Royal','Epic','Mythic','Eternal'))
        OR (kind = 'event' AND rarity IS NULL)),
    CHECK (NOT is_active OR (media_asset_ref IS NOT NULL AND length(trim(media_asset_ref)) > 0))
);
CREATE INDEX IF NOT EXISTS cards_active_selection
    ON gacha.cards (drop_key, rarity, card_id) WHERE kind = 'standard' AND is_active;

-- Duplicate cards are recorded as quantities, not overwritten or discarded.
CREATE TABLE IF NOT EXISTS gacha.player_cards (
    player_id bigint NOT NULL REFERENCES gacha.players(id) ON DELETE RESTRICT,
    card_id text NOT NULL REFERENCES gacha.cards(card_id) ON DELETE RESTRICT,
    quantity bigint NOT NULL CHECK (quantity > 0),
    first_obtained_at timestamptz NOT NULL DEFAULT now(),
    last_obtained_at timestamptz NOT NULL DEFAULT now(),
    PRIMARY KEY (player_id, card_id)
);

-- A single immutable authoritative result per (player, client_request_id).
CREATE TABLE IF NOT EXISTS gacha.spins (
    spin_id uuid PRIMARY KEY,
    player_id bigint NOT NULL REFERENCES gacha.players(id) ON DELETE RESTRICT,
    client_request_id uuid NOT NULL,
    game_day date NOT NULL,
    attempt_kind text NOT NULL CHECK (attempt_kind IN ('daily', 'bonus')),
    rarity text NOT NULL CHECK (rarity IN ('Classic','Elite','Royal','Epic','Mythic','Eternal')),
    card_id text NOT NULL REFERENCES gacha.cards(card_id) ON DELETE RESTRICT,
    drop_key text NOT NULL DEFAULT 'main',
    odds_version smallint NOT NULL DEFAULT 1 CHECK (odds_version = 1),
    created_at timestamptz NOT NULL DEFAULT now(),
    UNIQUE (player_id, client_request_id)
);
CREATE INDEX IF NOT EXISTS spins_player_history ON gacha.spins (player_id, created_at DESC);

-- The delivery adapter (later PR) consumes this outbox. A confirmed spin is
-- never re-rolled because an HTTP response or Telegram callback is lost.
CREATE TABLE IF NOT EXISTS gacha.delivery_outbox (
    spin_id uuid PRIMARY KEY REFERENCES gacha.spins(spin_id) ON DELETE RESTRICT,
    state text NOT NULL DEFAULT 'pending'
        CHECK (state IN ('pending','sending','sent','uncertain','failed')),
    telegram_message_id bigint,
    error_code text,
    updated_at timestamptz NOT NULL DEFAULT now(),
    created_at timestamptz NOT NULL DEFAULT now()
);

COMMIT;
