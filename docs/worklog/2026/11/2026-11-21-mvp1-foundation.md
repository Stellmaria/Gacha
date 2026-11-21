# Gacha #22 — MVP-1: PostgreSQL game foundation

- Схема: 2
- Компоненты: `db/migrations/001_mvp1_core.sql`, `gacha_core/`, `tests_python/test_mvp1_*`, `.github/workflows/ci.yml`, `docs/MVP1_GAME_CORE.md`
- Приёмка: PG18 integration: регистрация, 10/сутки в 00:00 Europe/Moscow, сброс без накопления, bonus separate, Elite, six odds, repeat cards, immutable spin, idempotency, concurrency, outbox and wallet structure, failed spin rollback
- PR: pending
- Связанные issues: `#22`
- Связанные записи: `docs/worklog/2026/11/2026-11-21-wheel6-inline-reveal.md`

## Перед началом

- Владелица утвердила `Elite` (не Elegant), дубли карт, расход сначала daily затем bonus, 10 бесплатных круток ежедневно при одном сбросе 00:00 МСК, без накопления daily, бонусные не сгорают.
- Контент: исходно **по одной готовой карте на Classic/Elite/Royal/Epic/Mythic/Eternal и одна отдельная вельветовая адвент/ивент-карта**. Фактические файлы и точные IDs пока не обнаружены в `Stellmaria/Gacha`; ничего не генерировать и не выдавать за утверждённый оригинал.
- Baseline `Stellmaria/Gacha@423d6df61a6814e88c517599652944469254a50c`.
- Branch `feat/issue-22-mvp1-pg-game-core`.
- Bounded scope: PostgreSQL 18 schema and transactional game domain; precise UTC/Moscow tests, idempotency and guardrails. NO live bot, host allocation, payments or actual card image imports in this PR.
- Риски: аудируемость/распределение случайных исходов, replay across dates, database races, TOS/IP of original cards, transport-ambiguous Telegram events. Transactional persistence must precede any API delivery; deployment is a separate decision.

## Порядок проверки

- Apply migration to ephemeral PG18 service in GitHub Actions; fixture catalog appears only in tests, not production seed.
- Run Python unit + PostgreSQL integration and existing Node/browser/Telegram smoke tests.
- If CI passes: protected merge without production deploy; next bounded slice is permanent Telegram adapter and verified card asset import.
