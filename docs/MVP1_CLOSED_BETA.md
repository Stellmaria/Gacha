# Gacha MVP-1 · closed beta acceptance / operator gates

**GitHub issue:** [#28](https://github.com/Stellmaria/Gacha/issues/28). Gacha code has seven verified cards (#26) and a Telegram adapter (#27). Those merged PRs are **not** evidence of an installed or functioning public game.

## Actual current state, 22 Nov 2026

- Seven exact owner-uploaded original PNG files are available as **private** `Gacha_MVP1_7_approved_cards_private.zip`; compare their contents against `gacha_core/catalog/approved_cards.json`. Do not upload image binaries into public GitHub. The original private ZIP has been validated byte-for-byte in an isolated ChatGPT sandbox, **not deployed on a Gacha host**. Similar-named images on Stell-PC-Windows have different SHA-256 and cannot silently replace the approved originals.
- The existing Gacha `wheel` MP4s are original and validated; `/wheel6` manual visual test has previously passed but does **not** charge attempts or give cards.
- The connected Stell-PC-WSL currently offers a shared PostgreSQL 17 cluster with no local `aamch` role; it is **not** the required independent PostgreSQL 18 Gacha beta instance. Do not use Velvet production databases, shared CI runner identities or existing host services for beta by default.
- PostgreSQL 18 schema and transactional game rules have previously passed ephemeral CI. This PR adds a fresh snapshot/restore drill and preflight; real live card delivery still needs separate host+Telegram acceptance.

## Read-only preparation

`python -m gacha_core.beta_preflight --private-root /secure/gacha-card-assets` checks original wheel, exact seven PNG hashes, dedicated database name/PG18/version/migrations, privilege restrictions, approved active catalog and unresolved ambiguous sends. It returns a JSON list of findings; **exit status 2 means BLOCKED**. It does not call Telegram unless `--online` is added explicitly and protected `GACHA_BOT_TOKEN` plus `GACHA_EXPECTED_BOT_USERNAME` exist. `--online` only does `getMe` and `getWebhookInfo` (no polling, no webhook changes, no messages).

`python -m gacha_core.beta_reconcile` produces a **read-only, redacted** summary of delivery outbox states and stale ambiguous sends. No Telegram ID, account detail or card image is included, and no resend happens.

A manual read-only bot identity workflow `.github/workflows/telegram-beta-identity-readonly.yml` checks only the existing approved test bot's `getMe/getWebhookInfo`. It must not be interpreted as proof that no concurrent long-polling worker is active, nor as permission to launch one.

## Operator runbook — requires verified independent target and explicit launch permission

1. Choose a separate Gacha beta host, independent PostgreSQL 18 database named e.g. `gacha_beta` and a non-superuser, non-createdb, non-createrole runtime user. Restrict firewall and Telegram token, backup storage, disk quotas. Never use production Velvet/Diamond DB or CI-02 runner capacity.
2. Confirm the bot token and exactly one operator-controlled update consumer. The existing `@velvet_gacha_v1_bot` is also used by manual GitHub Actions smoke workflows; disable or exclude those before attaching a persistent Gacha poller, or use a separate beta bot. Do not reassign/delete Telegram webhooks without owner-approved handoff.
3. On the private host only, place the **exact** seven-card ZIP outside Git checkout, with restrictive permissions. Execute `python -m gacha_core.card_store --bundle /secure/Gacha_MVP1_7_approved_cards_private.zip --private-root /secure/gacha-assets` and record 7/7 validation; never copy private PNGs to GitHub artifacts/logs.
4. Make an encrypted, restorable backup before schema mutations. Apply migrations `001`–`003` using `python -m gacha_core.migrate` against a dedicated Gacha database. In that host and only then, re-run private card installer with `--register`. No fake initial cards or event #22 included in standard wheel.
5. Check `python -m gacha_core.beta_preflight --private-root /secure/gacha-assets --online`; all checks must be PASS. Resolve ambiguous outbox first via the read-only reconciler, never blindly mark it `sent` or resend.
6. Explicitly configure `GACHA_ENABLE_POLLING=YES`, `GACHA_EXPECTED_DATABASE_NAME=gacha_beta`, `GACHA_EXPECTED_BOT_USERNAME` to the approved beta bot, and other secrets in protected runtime. Use a single operator-managed service with stop/restart procedures; **do not** let CI create a persistent process.
7. Closed owner/Tanya tester acceptance (no public link): `/start` shows 10/10, `/spin` charges exactly once and edits original wheel to selected MP4; correct image appears and persists in `/cards`, duplicate `×2` increments; `/history` includes exact card; event #22 cannot drop. Verify mobile and desktop rendering, repeat callbacks and separate accounts, 00:00 Europe/Moscow reset and bonus precedence.
8. Test mid-flight interruption with two separate, controlled test accounts. If Bot API acknowledgement is ambiguous, DB still has the reward and outbox is `uncertain`; no automatic resend. Confirm manual reconciliation procedure and rollback (stop poller, retain data, restore backup if needed). Monitor database disk, connections and failures. Public rollout and monetization remain separate approvals.

## CI backup/restore drill (safe synthetic data)

`scripts/mvp1_backup_restore_ci.sh` accepts **only** GitHub Actions with the exact ephemeral `gacha_ci` test connection. It prepares one synthetic Classic reward and 3 bonus attempts, runs `pg_dump` with the same PostgreSQL 18 container, restores into newly created `gacha_restore_ci`, verifies all three migration records, user ID, inventory quantity, outbox, 9/10 daily and 3 bonus attempts and that replay returns the original spin without another charge. No private PNG, real bot or prod database are used. When the job exits, the CI service container is destroyed.

## Current acceptance gate

- Verified real art archive in isolated environment: **DONE** (7/7 original bytes).
- Backend, original image registry and Telegram delivery code: **MERGED** (#23, #26, #27).
- PostgreSQL 18 integration + dump/restore drill: **CI EVIDENCE REQUIRED**.
- Authorized dedicated Gacha runtime target, credential provisioning and full private image installation: **NOT DONE**.
- Real one-spin Telegram delivery with persistent DB and two-user closed beta: **NOT DONE**.
- Public release, payments, Stars, advent event distribution: **NOT AUTHORIZED**.

Do not close #28 or announce a running beta until the last two acceptance blockers are completed with live evidence. This issue does not automatically authorize unsafe production access or a second Telegram poller.
