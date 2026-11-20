# Gacha #11 — exact original transparent GIFs in Telegram

- Source: the six GIFs from the owner's archive `Gacha_six_rarities_transparent_GIF.zip` in Windows Downloads.
- Local archive integrity: PASS; filenames are strict whitelist; GIF89a header and dimensions verified.
- 450×450, 64 frames, about 5.94s each; total archive uncompressed size ~44 MB.
- Import: `assets/roulette/original_gifs/gacha_{classic,elite,royal,epic,mythic,eternal}.gif`.
- SHA256 digest of every file pinned in `scripts/ornate_wheel.py`; CI checks full hashes + alpha and playback duration, not merely renderer logic.
- Removed fallback branch from live `render_ornate_gif`. Missing/mutated originals fail-closed.
- Preserved neutral animation caption and separate delayed rarity reveal; no actual rewards are granted.
- Existing test-purpose bot `@velvet_gacha_v1_bot`; `GACHA_TEST_BOT_TOKEN`; workflow is manual-only.
- No deployment to Velvet. Real Telegram smoke requires manual dispatch following merge.
