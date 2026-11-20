# Куда сохранять Telegram Bot API Token

В репозитории `Stellmaria/Gacha` токены хранятся только в **GitHub Actions repository secrets**.
Код/README/issues/PR/чат не являются хранилищем токенов.

Откройте:
https://github.com/Stellmaria/Gacha/settings/secrets/actions

`Settings → Secrets and variables → Actions → Secrets → New repository secret`

Создайте:

| Название GitHub Secret | Что вставлять | Применение |
| --- | --- | --- |
| `GACHA_BOT_TOKEN` | Токен обычного Telegram-бота из основного BotFather | Ручная проверка в production Bot API |
| `GACHA_TEST_BOT_TOKEN` | Токен **отдельного бота** в Telegram Test Server | Ручная проверка в Test Bot API |

Не создавайте тестовый secret с основным токеном. У Telegram Test Server отдельные аккаунты и боты.

**Никому не присылайте токены** — в том числе ChatGPT. Не передавайте их как inputs workflow.
Telegram bot token даёт управление ботом; если он случайно опубликован — регенерируйте его через BotFather.

## Как проверить без запуска сервера

После появления `.github/workflows/telegram-preflight.yml` в `main`:

1. Откройте https://github.com/Stellmaria/Gacha/actions/workflows/telegram-preflight.yml
2. `Run workflow` → выбрать `test` или `production`.
3. Запуск на GitHub-hosted `ubuntu-latest` выполнит **только `getMe`**.
4. Проверка печатает только публичный username бота и выбранное окружение. Токен и полный URL не выводятся.
5. Секреты не открываются в обычных `push` и `pull_request` проверках проекта.

Workflow добавлен в `main` при merge PR #2. 20.11.2026 его тестовый запуск №44791230783 вернул **HTTP 401**. Если выбран `test`, а сохранён обычный BotFather-токен, он работать не будет: создайте отдельного бота из тестового аккаунта Telegram. Обновлённая проверка (Issue #3) безопасно классифицирует такой случай через read-only `getMe` в обоих окружениях; сами токены никогда не выводятся.

## Ограничения

- Добавление настоящего secret осуществляется владельцем в GitHub Settings, а не через pull request: GitHub connector имеет доступ к файлам, но не к API изменения секретов.
- Preflight `getMe` проверяет правильность токена и доступность Bot API, **не** работу рулетки, Widgets или приём сообщений.
- GitHub Actions не является постоянно работающим сервером Telegram. Для вебхука и учёта вращений позже потребуется отдельный runtime с собственным безопасным хранилищем токенов.
- В публичном репозитории даже `Actions` и CI logs могут видеть другие участники/посетители. Поэтому никаких секретов в output, curl debug, shell `set -x` или workflow inputs.

Официальная документация: https://docs.github.com/en/actions/how-tos/write-workflows/choose-what-workflows-do/use-secrets и https://core.telegram.org/bots/features#testing-your-bot

## Пробное вращение в Telegram Test Server

После того как тестовый `getMe` успешно проверит токен, отправьте **`/wheel`** в личный чат тестового бота, затем на GitHub запустите `Telegram Widget smoke` вручную. В течение примерно 90 секунд после отправки Widget нажмите в нём «Крутить». Это краткосрочный smoke, **без начисления карты/вельветов и без работающего в фоне бота**.

Запуск smoke требует именно Test Server; в основной Telegram он сообщения не отправляет. Проверка отклоняет неоднозначный выбор нескольких адресатов. Токены не передаются через inputs.
