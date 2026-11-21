# Gacha Issue #18 — Telegram Royal MP4 manual smoke

- Схема: 2
- Компоненты: `scripts/telegram_royal_mp4_smoke.py`, `.github/workflows/telegram-royal-mp4-smoke.yml`, `tests_python/test_telegram_royal_mp4_smoke.py`
- Приёмка: SHA256 исходного MP4 и PNG, Telegram multipart contract, callbacks owner-only, manual-only workflow, no charges, CI PASS; live acceptance separate
- PR: #19
- Связанные issues: `#18`
- Связанные записи: `docs/WHEEL_ALL_OUTCOMES_IMPORT_2026-11-21.md`, `docs/GACHA_CHAT_ROYAL_TGS_PILOT.md`

## Перед началом

- Цель: показать в обычном личном чате Telegram только один утверждённый исход Royal, без Mini App и новых TGS-стикеров.
- Исходный контекст: утверждённый визуальный HTML Canvas и шесть MP4 из `wheel/videos`, импортированные в Gacha PR #17; прошлый TGS-пилот был визуально отклонён пользователем.
- Планируемый объём: **отдельный** ручной GitHub Actions workflow; точная команда `/royaltest` от одного частного отправителя; стартовое изображение из `wheel/source/master.png`, настоящая анимация `wheel/videos/Royal.mp4` через Telegram `sendAnimation`, задержанный текст результата.
- Граница: никакого бота на постоянной основе, Mini App, нового получателя, списания/выдачи награды, изменения существующих сценариев, открытия доступа к токенам.
- Риски: Telegram может преобразовать/зациклить MP4; сообщение после задержки измеряется от подтверждения upload, не от визуального завершения на клиенте. Отдельный live-тест обязателен.
- Базовый SHA: `main@06a37b0db3bf6166b85834133c5196df76634a9e`.
- Ветка: `feat/issue-18-approved-royal-mp4-chat-demo`.
- Готовность: exact file checksums, URL-safe errors, no misrouting in callbacks, unit/CI and separately live confirmation.

## Изменения и локальная проверка

- Исходный Royal.mp4 и master.png не изменены; перед отправкой производится проверка SHA-256.
- Отдельный manual-only workflow и безвозмездный in-chat demo без постоянного сервера.
- Локальные проверки: Python `unittest discover`: 49 PASS (5 skipped без Pillow); `node --test`: 16 PASS; `git diff --check`: PASS.
- После PR live Telegram пока не запускали: требуется новый `/royaltest` и нажатие владелицы.
