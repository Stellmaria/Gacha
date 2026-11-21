-- Bound callback intents and restart-aware uncertain delivery state.
BEGIN;
CREATE TABLE IF NOT EXISTS gacha.telegram_spin_intents (
    intent_id uuid PRIMARY KEY,
    player_id bigint NOT NULL REFERENCES gacha.players(id) ON DELETE RESTRICT,
    telegram_user_id bigint NOT NULL CHECK (telegram_user_id > 0),
    chat_id bigint NOT NULL CHECK (chat_id > 0),
    message_id bigint CHECK (message_id > 0),
    state text NOT NULL DEFAULT 'prepared'
        CHECK (state IN ('prepared','ready','committed','expired')),
    spin_id uuid UNIQUE REFERENCES gacha.spins(spin_id) ON DELETE RESTRICT,
    created_at timestamptz NOT NULL DEFAULT now(),
    expires_at timestamptz NOT NULL,
    CHECK (expires_at > created_at),
    CHECK ((state='prepared' AND message_id IS NULL AND spin_id IS NULL)
        OR (state='ready' AND message_id IS NOT NULL AND spin_id IS NULL)
        OR (state='committed' AND message_id IS NOT NULL AND spin_id IS NOT NULL)
        OR (state='expired' AND spin_id IS NULL))
);
CREATE INDEX IF NOT EXISTS telegram_intents_player ON gacha.telegram_spin_intents(player_id,created_at DESC);
ALTER TABLE gacha.delivery_outbox
    ADD COLUMN IF NOT EXISTS wheel_message_id bigint,
    ADD COLUMN IF NOT EXISTS card_message_id bigint;
CREATE TABLE IF NOT EXISTS gacha.telegram_poll_cursor (
    singleton boolean PRIMARY KEY DEFAULT true CHECK (singleton),
    last_update_id bigint NOT NULL DEFAULT -1,
    updated_at timestamptz NOT NULL DEFAULT now()
);
COMMIT;
