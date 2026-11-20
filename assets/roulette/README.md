# The approved original roulette GIFs

These six GIFs are the **exact, user-approved transparent animations**, imported from `Gacha_six_rarities_transparent_GIF.zip` on 2026-11-20. There are no generated substitute GIFs during Telegram delivery.

All files are 450×450, 64 frames, ~5.94 seconds; one per rarity: Classic 25%, Elite 22%, Royal 19%, Epic 16%, Mythic 11%, Eternal 7%. Rarity is selected by the server, **not** by visual sector size.

Files and exact SHA256 values are embedded in `scripts/ornate_wheel.py` and verified by CI. The old `ornate-wheel.svg` is an inactive design reference and is never used by this bot.

If any original asset is missing or modified, animation delivery fails closed rather than silently replacing the original with an SVG. The animation caption remains neutral, then the chosen rarity is revealed after the timed delay.

Since Telegram has no reliable client playback-completion callback, the 7.5-second reveal delay starts after `sendAnimation` returns; some clients may begin playback later.
