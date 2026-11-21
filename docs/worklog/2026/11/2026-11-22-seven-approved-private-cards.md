# Gacha #24 — Import seven source-verified cards, private local storage

- Схема: 2
- Компоненты: `gacha_core/catalog/approved_cards.json`, `gacha_core/card_store.py`, `tests_python/test_mvp1_card_store.py`, `docs/MVP1_CARDS.md`
- Приёмка: 7 exact hashes of owner-provided PNGs, metadata, private storage, repeatable catalog import, event excluded from six rarities, no publish of images
- PR: pending
- Связанные issues: #24
- Связанные записи: `2026-11-21-mvp1-foundation`

## Перед началом

- Владелица прислала семь полноразмерных PNG в чат и подтвердила: 6 обычных и Эйдан/Velvet — только event, вне daily wheel.
- Baseline: `Stellmaria/Gacha@c23d2c6acb596b1ff030fdc1289d78770b3e5cec` (main), branch `feat/issue-24-seven-verified-private-cards`.
- План: зарегистрировать точные ID, имена, редкости, SHA-256, разрешения, размер файлов; безопасный private bundle importer без публичного арта. Проверить идемпотентность и fail-closed. Связать с `gacha.cards` для выбора и выдачи через будущий Telegram adapter.
- Границы: не публиковать PNG в публичный GitHub, не создавать новые карты, не подключать живой Telegram или production, не раскрывать скрытые данные.
- Критерии: проверки семи оригиналов и отсутствия подмен; точное семантическое разделение standard/event; PostgreSQL-backed каталог; тесты безопасного zip и приватного хранилища.

## Реализация и проверка

- Seven exact owner-uploaded PNG SHA-256 hashes recorded in manifest; original image archive stays off public GitHub (separate private package).
- `install_bundle` validates all seven exact original bytes before storing under non-repo private root, rejects unexpected zip paths / modified images / symlinks, writes restricted 0600 files.
- `register_approved_cards` idempotently registers original metadata/number and activates six main + one isolated event; refuses overwriting changed card identity. PostgreSQL migration #002 adds card labels and media SHA.
- CI: existing wheel + new eight offline tests; PG18 migration and real catalog integration test, when available.
- No Telegram, server or public deployment. Image delivery by SHA-checked bytes is prepared; actual Telegram adapter is separate #25.
