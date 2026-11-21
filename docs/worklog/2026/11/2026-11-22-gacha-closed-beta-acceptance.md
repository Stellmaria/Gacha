# Gacha #28 — staged closed-beta preflight, recovery and acceptance gates

- Схема: 2
- Компоненты: `gacha_core/beta_preflight.py`, `gacha_core/beta_reconcile.py`, `scripts/mvp1_backup_restore_ci.sh`, `tests_python/test_mvp1_beta_preflight.py`, `.github/workflows/ci.yml`, `docs/MVP1_CLOSED_BETA.md`
- Приёмка: private original 7 PNG SHA verified, PG18 isolated backup/restore test, secure fail-closed preflight, sanitized operator reconciliation, all existing Python/Node/Gacha CI, no unauthorized live Telegram or production deployment
- PR: pending
- Связанные issues: #28
- Связанные записи: `2026-11-21-mvp1-foundation`, `2026-11-22-seven-approved-private-cards`, `2026-11-22-mvp1-telegram-adapter`

## Перед началом

- Canonical owner Issue #28; base `Stellmaria/Gacha@3452fe052b36d77e3bb5ffbfa11635731624e5e8`; isolated branch `feat/issue-28-closed-beta-acceptance-gates`.
- Owner instructed to proceed on 2026-11-22 after #26 (catalog) and #27 (Telegram adapter) merged. Scope: prepare and VERIFY safe closed-beta prerequisites without touching Velvet production, switching service tokens, starting conflicting Telegram pollers or exposing approved PNG in public GitHub.
- Environment survey: connected Stell-PC-WSL has PostgreSQL 17 cluster with no local `aamch` role, NOT an approved independent PostgreSQL 18 Gacha host. Shared CI-02 runners must not be reused as Gacha production. The exact seven approved PNG originals exist inside a private conversation ZIP, NOT the different local same-named files on the Windows Downloads drive.
- Plan: verify exact ZIP hash locally; add deterministic independent preflight, read-only uncertain delivery ledger, exact PG18 dump/restore CI drill and isolated/offline acceptance tests. Capture pass/fail and blockers. Do not declare live Telegram acceptance without real API evidence.
- Criteria: no app import starts network; preflight is read-only; wrong DB/privileged role/changed PNG/missing catalog or active webhook fail closed; backup restore has a real fixture outcome and identity continuity; CI green; documented opt-in operator runbook.
- Risk constraints: Telegram may already be used by manual `/wheel6` workflow. No second poller without separate bot or explicit checked handoff. No ambiguous delivery auto resend, no destructive DB operations outside an ephemeral CI database.

## Выполнено до CI

- Verified the exact seven approved owner-uploaded private PNGs in an isolated ChatGPT sandbox (7/7 original SHA-256, 0700 directory/0600 image files, never sent to GitHub or Telegram). This is **not** installation on the operator-selected dedicated host.
- Created read-only `beta_preflight` (MP4/card SHA, independent PG18 DB+role, three migrations, seven active approved registry records, ambiguous delivery, optional read-only Telegram identity check).
- Created privacy-safe `beta_reconcile` (only aggregate counts, no automatic redelivery). Created manual Bot API `getMe/getWebhookInfo` identity-only workflow with existing preauthorized test secret.
- Created `mvp1_backup_restore_ci.sh` strictly limited to GitHub Actions and exact ephemeral `gacha_ci`; job will test restored migrations, one card, outbox, bonus and same-spin idempotency.
- Added two complete PostgreSQL 18 mocked-transport e2e tests: original six rarity selection, callback replay, real DB inventory/daily decrement/doubles and ambiguous delivery quarantine.
- Local WSL: 120 Python tests OK (25 intentionally skipped for missing real PG/PIL runtime), 16 Node tests PASS, compile+diff PASS; backup script hard-rejects non-CI invocation.
- No new PostgreSQL roles, services, CI-02 runner changes, Gacha production deployment, persistent polling, or message sending.
