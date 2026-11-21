# Gacha #25 — always-on Telegram adapter, card delivery, safety guards

- Схема: 2
- Компоненты: `gacha_core/telegram_adapter.py`, `gacha_core/telegram_runtime.py`, `db/migrations/003_telegram_adapter.sql`, `tests_python/test_mvp1_telegram_adapter.py`, CI, docs
- Приёмка: approved 7 local private cards, six original MP4 in ordinary Telegram chat, profile, daily attempts, double-click and retry, bound callbacks, idempotent result, private image delivery, uncertainty quarantine, CI PG18 & mocked API, no live deploy
- PR: #27
- Связанные issues: #25
- Связанные записи: `2026-11-21-mvp1-foundation`, `2026-11-22-seven-approved-private-cards`

## Перед началом

- Canonical owner issue #25; base `Stellmaria/Gacha@3df2ad126f00f2c841d00b3c3c90d7e28dc4ffb3` (first merged seven-card catalog PR #26), isolated branch `feat/issue-25-mvp1-telegram-adapter`.
- Goal: build an **opt-in** independent Telegram Bot API polling adapter; `/start`, `/profile`, `/cards`, `/history`, and one-button `/spin` with authoritative server selection and exact original image after animation. Existing manual smoke remains unchanged.
- Bound: private chats only, callback tied to account/chat/message/one opaque intent UUID; `GameCore.spin` transaction persists reward and outbox before any media API call. Ambiguous media sends marked `uncertain`, never automatically repeated. Stop duplicate polling via PostgreSQL advisory lock. No hosting, network, key use, user message, live deploy or real transaction in this PR.
- Risks: polling conflict with existing manual smoke on same bot token, network ambiguity and limited ability to prove a Telegram client finished playback; separate visual review and one-time deployment approval required.

## Acceptance

- Unit tests mock every Telegram API request; integration tests run only ephemeral `gacha_ci` PostgreSQL 18, verify callback ownership/replay and outbox state.
- A fully verified private card ZIP must be installed in live runtime before activating catalog. Event Velvet #22 never drops from daily wheel.

## Реализация (до CI)

- PostgreSQL intent binding by UUID, Telegram user/chat/message and TTL, transactional callback + GameCore.spin.
- Only verified six standard cards can be selected. Original approved wheel MP4 before exact privately stored PNG.
- Outbox quarantines ambiguous delivery; API retry does not reroll/recharge or resend card.
- Opt-in polling requires private env and exact bot name and no existing webhook; PostgreSQL advisory lock and persisted cursor.
- Unit Telegram Bot API is mocked; no real messages sent. Separate closed beta acceptance still needed.

- Local exact checks: Python 110 tests, 23 skipped locally (PG integration + optional imaging); JavaScript 16 PASS; no Bot API calls.
- Safety hardening: runtime now requires an approved database name and non-superuser role and pre-verifies all seven active catalog records/checksums before starting; the ordinary bot username must match and no webhook may exist.
- Existing manual `/wheel6` remains functionally unchanged; the editor now accepts an optional non-demo caption for real card delivery.
- Live behavior and deployment still NOT validated/authorized.
