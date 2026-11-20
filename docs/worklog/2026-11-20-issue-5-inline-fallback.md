# 2026-11-20 — ordinary Telegram six-rarity wheel fallback

- Owner issue: https://github.com/Stellmaria/Gacha/issues/5
- Baseline: `main` SHA `8322e56558f1f9f9d6c2762bb26d44790d165a68`
- Branch: `feat/issue-5-inline-wheel-fallback`
- PR: pending
- Objective: user can inspect true Telegram bot inline-click and roulette animation without HTML Widgets or Velvet server.
- Risk guard: manual workflow only, `GACHA_BOT_TOKEN`, no payment, no Telegram production service deployment, no prize grants, caller strictly bound to private /wheel.
- Implementation: Python stdlib Telegram Bot API, Pillow GIF renderer, offline tests, documentation.
- Acceptance: repository + GitHub Actions CI; real bot interactive test separate and still pending.
- Test Server blocked: [run 44793387784](https://github.com/Stellmaria/Gacha/actions/runs/44793387784) determined GACHA_TEST_BOT_TOKEN belongs to production environment; do not repurpose.
- Status: code in progress; live check not performed.
