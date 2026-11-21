# Gacha MVP-1 · Telegram ordinary bot adapter (prepared, NOT DEPLOYED)

This slice implements a real PostgreSQL-backed Telegram Bot API adapter, but **does not run** without explicit operator configuration and deployment approval. No Telegram Mini App, no payments, no Stars and no touch to Velvet/Dominus/Demian production.

## Telegram user-facing commands

- `/start` or `/profile` — account and daily 10/10 attempts, persistent bonus attempts, internal wallet; reset 00:00 Europe/Moscow.
- `/spin` or reply keyboard **«Крутить колесо»** — original PNG wheel cover plus a single inline button. A fresh server-generated UUID is stored as an intent bound to `(telegram_user_id, chat_id, original message_id)` for 15 minutes. Other users, groups, bots, forwarded/spoofed/expired messages cannot spend an attempt.
- After click: server atomically commits one selected rarity/card, spends daily before bonus, writes inventory duplicate quantity and transactional outbox. Replayed callback returns the same result and **never sends a second animation or card**.
- Wheel replaces cover with the original checked MP4 (Classic, Elite, Royal, Epic, Mythic, Eternal), waits nominal 12 seconds after Telegram API acceptance, reveals rarity by editing caption and then sends the **exact owner-supplied PNG** as the awarded card in a separate Telegram photo. Private asset resolver checks SHA-256 on every read. Velvet #22 remains `kind=event`, excluded from the ordinary daily wheel.
- `/cards` or **«Моя коллекция»** — inventory, including duplicates `×N`, rarity, title and number. `/history` — latest server-confirmed spins.

## Recovery, identity and safety

- No event handler is launched on import. Starting the poller requires all of `GACHA_ENABLE_POLLING=YES`, `GACHA_BOT_TOKEN`, `GACHA_EXPECTED_BOT_USERNAME`, `GACHA_DATABASE_URL`, `GACHA_PRIVATE_CARD_ROOT` from authorized private runtime; no credentials committed.
- Script: `python -m gacha_core.telegram_runtime` only after operator-approved independent test deployment, PostgreSQL migrations #001–#003, private seven-card archive installation and `--register` activation.
- Operator must ensure there are no simultaneously running manual GitHub Telegram smoke workflows (`/wheel6`/`/royaltest`), and no webhook attached to the bot. Before polling, the runtime checks the exact bot username, webhook absence, private PNG checksums, and takes one session advisory DB lock to forbid two instances of this Gacha polling process. First boot discards stale queued Telegram updates.
- A delivery outbox row goes into **`uncertain` before network media calls**. Only a confirmed result photo `message_id` marks it `sent`. A timeout, crashed process or unknown Bot API result leaves `uncertain`, **never automatically redelivers** or re-charges. The earned card is already in the inventory and can be reconciled by an operator. This sacrifices automatic recovery for avoiding duplicate sends. The poll cursor persists in PostgreSQL to support restart.
- Telegram does not provide an event confirming the client finished the animation. The 12-second reveal is approximate.
- This initial sequential worker is suitable for **controlled low-volume beta only**, not production scale. Repeated timeouts, errors and incompatible media must be monitored before public release.

## Tests

- `test_mvp1_telegram_adapter.py` mocks Telegram media APIs and checks private chat / callback parsing, same-message binding, duplicate replay, actual card dispatch ordering, uncertainty handling and launch gates.
- `test_mvp1_postgres.py` checks actual PostgreSQL 18 callback binding, expiry, two users, concurrent same callbacks, durability and outbox quarantine. Existing tests verify daily reset, duplicates, and approved seven-card separation.
- CI uses a temporary PostgreSQL 18 service. It must never access production Telegram tokens or send real messages.

**Not done here:** private ZIP installation on an authorized host, real test bot deployment, live Telegram acceptance, external asset rights review, admin reconciliation UI, load tests and public launch. All require a separate operator decision.
