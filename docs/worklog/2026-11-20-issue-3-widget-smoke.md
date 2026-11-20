# 2026-11-20 — Telegram test server widget smoke

- Owner Issue: https://github.com/Stellmaria/Gacha/issues/3
- Base: `main` at `b31fa7a9e8bb3670d3546271e6a267c4fd8553e1`
- Branch: `feat/issue-3-telegram-widget-smoke`
- PR: pending
- Goal: diagnose HTTP 401 from run 44791230783 and test one real Telegram Widget in a separate TEST environment using a short-lived, manually triggered GitHub Actions workflow.
- Scope: preflight 401 diagnosis via both read-only getMe endpoints; self-contained six-rarity HTML Widget; isolated manual `/wheel` smoke with server-authoritative demo spin and editMessageWidgetData; offline tests and docs.
- Risks: test token may actually belong to production; no secret readable; widget may be disabled on user's client; queue polling can consume test-only updates; only one test chat; GitHub Actions is not a persistent bot runtime.
- Acceptance: exact-head CI on GitHub-hosted runner, plus separate TEST Bot API live smoke after correct secret is available.
- Status: implementation in progress. No product award, no payment, no public deploy, no changes to Velvet servers.
