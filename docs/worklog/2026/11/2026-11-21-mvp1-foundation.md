# Gacha #22 — MVP-1: PostgreSQL game foundation

- Схема: 2
- Компоненты: `db/migrations/001_mvp1_core.sql`, `gacha_core/`, `tests_python/test_mvp1_*`, `.github/workflows/ci.yml`, `docs/MVP1_GAME_CORE.md`
- Приёмка: PG18 integration: регистрация, 10/сутки в 00:00 Europe/Moscow, сброс без накопления, bonus separate, Elite, six odds, repeat cards, immutable spin, idempotency, concurrency, outbox and wallet structure, failed spin rollback
- PR: #23
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

## Фактически выполнено и проверено

- Код: схема `gacha`, PostgreSQL core, idempotency key and player locks, exact Moscow game-day, separate bonus, event card category distinct from standard six.
- Первое PostgreSQL CI упало до изменения БД: парсер миграции не учитывал комментарий перед `BEGIN;`. Исправлено в b6a15fe, повторный PostgreSQL 18 CI PASS.
- Интеграционные тесты ограничены одноразовой CI-базой `gacha_ci`/role `gacha_ci` до `TRUNCATE`.
- Локально: Python 80 OK, из них 19 skipped (14 PG integration без отдельной БД); Node 16 PASS; на GitHub isolated PG18 migration and integration tests PASS.
- Live/Gacha production deploy **не выполнялся**; следующее — source-verified 7 card images and secure Telegram adapter, separate PR/acceptance.
