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

## Production-host closed-beta safety gate (#28)

The initial production install is **closed beta only**, not a public launch. The
runtime must refuse to poll until `GACHA_BETA_ALLOWED_USER_IDS` contains 2–20
**distinct numeric Telegram user IDs**, comma-separated with no spaces. IDs are
private operator configuration (not committed, not printed in issue/CI/logs).
The Telegram adapter rejects both ordinary messages and callbacks from anyone
not in that allowlist **before DB writes or media requests**. The read-only
preflight reports allowlist presence and tester count, never actual IDs.

The opt-in systemd template is `deploy/systemd/gacha-beta.service`. Merely
adding this template to GitHub neither installs nor enables the unit. It expects
a dedicated `gacha` OS service identity, a verified code checkout at
`/opt/gacha/current`, a virtualenv at `/opt/gacha/venv`, protected
`/etc/gacha/beta.env` (permissions 0600) and read-only, owner-approved
cards in `GACHA_PRIVATE_CARD_ROOT` outside the checkout. A dedicated
PostgreSQL **18** database/role and rollback-tested backup are mandatory.
Install nothing on Velvet's canonical runtime checkout or CI runners.
The production host must be selected and inspected before using this unit.

Operator order of operations (do **not** skip gates):

1. Select a separately administered host without sharing Velvet/Diamond
   database or VPN/CI service roles; inspect memory, disk, backups, firewall.
2. Verify a dedicated PostgreSQL 18 target and non-superuser Gacha role.
   Stage an encrypted restorable backup before any migrations. Apply only
   migrations 001–003 against the exact expected `gacha_beta` DB.
3. Transfer the **original** owner-approved ZIP through a private channel;
   verify seven SHA-256 hashes and register the seven catalog records.
   No replacement artwork or public GitHub image artifacts.
4. Securely provision the bot token on the host, verify exact bot username
   and webhook absence. The existing test bot is also used by manual
   GitHub Actions Telegram workflows: hand off exclusive `getUpdates`
   ownership and suspend overlapping manual runs **before** polling.
5. Set `GACHA_EXPECTED_DATABASE_NAME=gacha_beta`,
   `GACHA_EXPECTED_BOT_USERNAME`, `GACHA_DATABASE_URL`,
   `GACHA_BOT_TOKEN`, `GACHA_PRIVATE_CARD_ROOT`,
   `GACHA_BETA_ALLOWED_USER_IDS` and only then
   `GACHA_ENABLE_POLLING=YES` in the protected env file.
6. Run `python -m gacha_core.beta_preflight --online`, inspect every PASS.
   Install the systemd unit but **do not enable/start it** if any preflight
   finding is BLOCKED or another Telegram poller may be active.
7. Start one supervised service; run the two-tester private Telegram
   acceptance checklist above and `python -m gacha_core.beta_reconcile`.
   If acceptance fails, stop the service while preserving DB, cards and
   outbox for review; never blindly repeat an ambiguous Telegram delivery.

No card trading, Stars, shop, paid mechanics, public announcement or event
card #22 drops are authorized by the beta deployment.
