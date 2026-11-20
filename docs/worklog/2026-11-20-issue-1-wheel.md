# 2026-11-20 — первый прототип рулетки

- Owner: https://github.com/Stellmaria/Gacha/issues/1
- Исходная ветка: main, commit `afc3e2c3ff7c7603bf6d6da67d0582a93e5ce34f`
- Рабочая ветка: `feat/issue-1-wheel-prototype`
- Статус: прототип, не production.
- Цель: визуально проверить два независимых колеса и алгоритм попадания стрелки в сервером заранее определённый сектор.
- Ограничения: только GitHub Actions; без приватных хостов, секретов, платежей, выдачи карт и Telegram-вызовов.
- Риск: Telegram HTML Widgets могут быть недоступны в production; браузерное демо не является Telegram-live приёмкой.
- Приёмка: unit + syntax checks на GitHub-hosted runner, отдельно требуется UI-проверка и возможность интеграции с Bot API.
- PR: pending.
