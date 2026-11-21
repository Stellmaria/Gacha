# Gacha #20 — six approved outcomes, one-message in-chat reveal

- Схема: 2
- Компоненты: `scripts/telegram_wheel6_smoke.py`, `tests_python/test_telegram_wheel6_smoke.py`, `.github/workflows/telegram-wheel6-smoke.yml`
- Приёмка: 6 оригинальных проверенных MP4; серверные веса 25/22/19/16/11/7; безопасная доставка и редактирование сообщения; bounded fallback; callbacks/CI; ручная живая приёмка отдельно
- PR: pending
- Связанные issues: `#20`
- Связанные записи: `docs/worklog/2026/11/2026-11-21-royal-mp4-chat-smoke.md`, `docs/WHEEL_ALL_OUTCOMES_IMPORT_2026-11-21.md`

## Перед началом

- Цель: довести положительно оценённый Royal MP4-пилот до UX всех шести редкостей с минимальным засорением Telegram-чата.
- Канонический источник: `Stellmaria/Gacha@ed17b4a2b1e4f7f46081a52c7162016052762413` — последний `main` на старте работы.
- Ветка: `feat/issue-20-wheel6-inline-reveal`.
- Объём: отдельный manual-only workflow для свежей команды `/wheel6` в одном приватном диалоге. Одна обложка и inline-кнопка; `editMessageMedia(InputMediaAnimation)` вместо нескольких сообщений; после номинального времени `editMessageCaption` с выпавшей редкостью. Предсказуемый fallback при явно подтверждённом отказе редактировать медиа; без fallback после network-ambiguous ошибок.
- Веса: 25/22/19/16/11/7; выбор сервером `secrets.randbelow(100)`, а не клиентом или по названию файла.
- Ограничения: никакого Mini App, TGS, подмены исходных MP4, начисления карт, платежей, постоянной службы, автоматических уведомлений или вмешательства в Velvet production; реальный клиент может зациклить/задержать ролик.
- Критерии готовности: проверки полного соответствия checksum всем шести видео, смоделированных ответов Telegram, запрета повторных нажатий, отсутствия раннего раскрытия, CI PASS, только после этого ручная проверка в Telegram с согласия владельца.

## Реализация и локальная проверка

- Базовый Royal-пилот оставлен нетронутым; новый `/wheel6` изолирован отдельным GitHub Actions workflow.
- Официальный `editMessageMedia` и `InputMediaAnimation` проверены по Telegram Bot API; fallback только на HTTP 400, а не на ambiguous network errors.
- 6 оригинальных MP4 и обложка валидируются по SHA256 и исходным углам; выбор сервером по весам, без клиента.
- Локально: `python -m unittest discover` — 61 PASS (5 skipped: PIL отсутствует на WSL), `node --test` — 16 PASS, `node --check` и `git diff --check` — PASS.
- Техническое `sendMessage` результата не используется: итог редактирует caption анимации.
- CI: не запускался до PR; live Telegram не запускался.
