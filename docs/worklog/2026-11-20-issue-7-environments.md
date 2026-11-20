# 2026-11-20 — fixed environment choice for one existing Gacha test-purpose bot

- Owner issue: https://github.com/Stellmaria/Gacha/issues/7
- Baseline main: `5200cb0fa4f317b1b1d7021698cf40301a00a98d`
- Branch: `fix/issue-7-bot-environment-selector`
- PR: pending
- Evidence: [GitHub Actions 44796501612](https://github.com/Stellmaria/Gacha/actions/runs/44796501612) shows latest `GACHA_TEST_BOT_TOKEN` is accepted in ordinary Telegram Bot API but rejected by `/test/getMe`. This proves the bot's **network environment**, not an erroneous GitHub secret.
- Goal: preserve owner's single test-purpose bot and distinguish it from special Telegram Test Server without forcing creation of a second bot.
- Change: default read-only `existing-test-bot` preflight uses `GACHA_TEST_BOT_TOKEN` on ordinary API; strict `telegram-test-server` option remains; manual inline/GIF smoke uses the same already configured secret; docs corrected.
- Safety: no token exposed; no automatic Telegram requests on push/PR; no new bots/servers/charges; no grant/ledger/card state.
- Verification: source unit checks + GitHub-hosted CI and explicit manual live run.
- Status: code candidate; live manual smoke not yet performed.
