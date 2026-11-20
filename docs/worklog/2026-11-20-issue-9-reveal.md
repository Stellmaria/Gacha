# 2026-11-20 — ornate wheel and delayed rarity reveal

- Canonical issue: https://github.com/Stellmaria/Gacha/issues/9
- Baseline: main at `bd372a5ab1f8d543af09c6b3334fe2bbee6a659b`
- Branch: `feat/issue-9-ornate-wheel-reveal`
- PR: https://github.com/Stellmaria/Gacha/pull/10
- Confirmed original problem: caption in `scripts/telegram_inline_smoke.py` included the winning rarity in the same sendAnimation request; recipients saw the outcome before playback completed.
- Solution: neutral caption, separate `sendMessage` reveal after at least 7.5 sec from media API acknowledgment; no reveal if media send fails.
- Visual: text-only SVG reconstruction of ornate six-sector transparent wheel; server picks rarity using 25/22/19/16/11/7, rotating dial targets the equal-width matching sector. All six original GIF names reserved under `assets/roulette/original_gifs/` (binary originals not yet committed).
- Checks at SHA `5c20dcd667d58ba76e5d114a474849019e31939d`: PR GitHub Actions https://github.com/Stellmaria/Gacha/actions/runs/44813296552 — both `wheel-tests` and `gif-render-test` PASS. Renderer job: 8 tests PASS in 18.035s, all 6 sectors/transparency and full-size 360×360 GIF. Manual Telegram workflow was NOT dispatched. The delayed-reveal/no-spoiler unit tests passed in the standard job.
- Safety: user-owned single testing bot only, existing manual-only workflow; no bills/cards/grants; no server deployment and no automatic dispatch.
- Remaining limitations: Telegram provides no playback-finished acknowledgment, so the delayed reveal is best effort, not synced to the client. **The 6 original uploaded 450×450 binary GIF files are NOT in this PR**; active artwork is a source-backed ornate SVG reconstruction until binary upload is available. This is not an original-asset fidelity signoff.
