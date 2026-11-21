-- MVP-1: immutable card labels and verified original-image checksum metadata.
BEGIN;
ALTER TABLE gacha.cards
    ADD COLUMN IF NOT EXISTS card_number integer CHECK (card_number BETWEEN 1 AND 9999),
    ADD COLUMN IF NOT EXISTS character_name text CHECK (character_name IS NULL OR length(trim(character_name)) BETWEEN 1 AND 120),
    ADD COLUMN IF NOT EXISTS subtitle text CHECK (subtitle IS NULL OR length(trim(subtitle)) BETWEEN 1 AND 200),
    ADD COLUMN IF NOT EXISTS media_sha256 text CHECK (media_sha256 IS NULL OR media_sha256 ~ '^[0-9a-f]{64}$');
COMMIT;
