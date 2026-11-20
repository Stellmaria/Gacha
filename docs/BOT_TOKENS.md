# Токен и окружение Telegram для Gacha

Владелец создала **одного бота для тестирования**. Важно различать предназначение бота и сеть Telegram, где его создали.

## Подтверждено на GitHub Actions

20.11.2026 повторный [run 44796501612](https://github.com/Stellmaria/Gacha/actions/runs/44796501612) показал: `GACHA_TEST_BOT_TOKEN` успешно принимается **обычным Telegram Bot API**, а `/test/getMe` возвращает 401.

Следовательно, **текущий бот создан в обычной сети Telegram и используется как тестовый по назначению**. Никакого второго бота только ради smoke базовых механик создавать не требуется. Токен не выводился в логи и не был прочитан агентом.

## Где хранить токен

GitHub Settings: https://github.com/Stellmaria/Gacha/settings/secrets/actions

**Сейчас достаточно одного секрета:**

| Secret | Значение | Ручные workflows |
| --- | --- | --- |
| `GACHA_TEST_BOT_TOKEN` | Токен текущего бота из BotFather | `existing-test-bot` и `Telegram wheel fallback — MANUAL DEMO` |

`GACHA_BOT_TOKEN` пока **не требуется**; этот секрет зарезервирован для возможного отдельного публичного production-бота в будущем.

## Проверка подключения текущего бота

- Открыть https://github.com/Stellmaria/Gacha/actions/workflows/telegram-preflight.yml .
- `Run workflow` → `existing-test-bot` (**значение по умолчанию**).
- GitHub-hosted runner выполняет только `getMe` через `https://api.telegram.org/bot<TOKEN>/getMe`.
- Успех подтверждает идентичность/авторизацию текущего бота, но не работу HTML Widgets.
- Старые failed runs, где был выбран специальный Test Server, останутся красными в истории — это нормально.

## Настоящий Telegram Test Server — отдельная среда

Для полной HTML Widgets-проверки нужен именно бот, созданный после входа в специальную Telegram Test Server среду отдельным аккаунтом. Тогда API выглядит как `https://api.telegram.org/bot<TOKEN>/test/getMe`. **Текущий токен нельзя заставить работать там изменением имени секрета, перезапуском CI или переименованием бота.**

Официальная инструкция: https://core.telegram.org/bots/features#testing-your-bot .

Если понадобится реальная приёмка HTML Widget, отдельный тестовый аккаунт и бот в этой среде — самостоятельный шаг. **Не заменяйте** `GACHA_TEST_BOT_TOKEN` токеном от Test Server для текущего обычного Telegram smoke без обновления workflows: сейчас его использует обычный бот-демо.

## Ручное вращение без HTML Widget

Уже подготовленный fallback отправит обычному тестовому боту /wheel inline-кнопку и GIF: [инструкция](TELEGRAM_INLINE_FALLBACK.md).

Не передавать токены в чат, Issues, PR, workflow inputs или файлы. Secrets добавляются владельцем в GitHub Settings. У `push`/`pull_request` CI нет доступа к Telegram Secrets.

Все Telegram-запросы с секретами — только по явному ручному `workflow_dispatch`. Нет постоянного runtime, карточек и оплаты.
