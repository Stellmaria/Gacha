# 2026-11-20 — ordinary Telegram six-rarity wheel fallback

- Owner issue: https://github.com/Stellmaria/Gacha/issues/5
- Baseline: `main` SHA `8322e56558f1f9f9d6c2762bb26d44790d165a68`
- Branch: `feat/issue-5-inline-wheel-fallback`
- PR: https://github.com/Stellmaria/Gacha/pull/6
- Objective: user can inspect true Telegram bot inline-click and roulette animation without HTML Widgets or Velvet server.
- Risk guard: manual workflow only, `GACHA_BOT_TOKEN`, no payment, no Telegram production service deployment, no prize grants, caller strictly bound to private /wheel.
- Implementation: Python stdlib Telegram Bot API, Pillow GIF renderer, offline tests, documentation.
- Acceptance: repository + GitHub Actions CI; real bot interactive test separate and still pending.
- Test Server blocked: [run 44793387784](https://github.com/Stellmaria/Gacha/actions/runs/44793387784) determined GACHA_TEST_BOT_TOKEN belongs to production environment; do not repurpose.
- CI exact head before worklog update: `4d30b4417c16b4d16d7f5441c40954f5401baa31`. PR run https://github.com/Stellmaria/Gacha/actions/runs/44795058827 success; push run https://github.com/Stellmaria/Gacha/actions/runs/44795049842 success; `wheel-tests` and real Pillow `gif-render-test` success. GIF render unit test generated and inspected all 6 animated GIF outputs.
- Status: code and isolated GIF render CI pass; live Telegram interaction still pending, no runtime deployed and no real rewards.
