Gacha C1 closed beta — operational workspace

Canonical game release: Stellmaria/Gacha main, pinned to 34c9a19126c76e5474ef1347898af7148f4840a7
Canonical Issue: https://github.com/Stellmaria/Gacha/issues/28

This directory is a separate Docker Compose project, not /srv/velvet.
Only the PostgreSQL service is enabled by default. Telegram bot is under profile 'live'
and requires operator-provided token, private approved 7-card ZIP and explicit tester allowlist.
Never use postgres credentials or Telegram tokens in commands shown to people.

Before starting bot:
- verify SHA-256 of all 7 cards against release/gacha_core/catalog/approved_cards.json
- install and register cards in own DB
- migrate database, encrypted backup and restore-test completed
- provision bot token to secrets/runtime.env mode 0600 and 2-20 tester IDs
- verify webhook unset, exclusive getUpdates ownership and --online preflight PASS
- explicitly start: docker compose --profile live up -d bot

Stop bot only: docker compose --profile live stop bot
Do not run docker compose down -v (destroys Gacha database).
Do not change production Velvet/Diamond containers.
