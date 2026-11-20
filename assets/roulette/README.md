# Gacha Wheel visual source

- `ornate-wheel.svg` — committed text-only **vector reconstruction** based on the six rarity palette and user-supplied dark-romance reference. Transparent outside the circular dial; stationary golden pointer is applied by `scripts/ornate_wheel.py` after rotating the dial.
- The six **original** user-generated GIFs are not yet in GitHub because the GitHub connector cannot upload mounted local binary assets directly. The SVG fallback is a usable visually related but **not pixel-identical** illustration. Never call it the six original GIFs.
- Once available, place *all six* GIFs under `assets/roulette/original_gifs/`: `gacha_classic.gif`, `gacha_elite.gif`, `gacha_royal.gif`, `gacha_epic.gif`, `gacha_mythic.gif`, `gacha_eternal.gif`. The renderer switches to them automatically only if the complete set exists, avoiding mixed artwork.
- Server-side chance weights stay **25/22/19/16/11/7**, regardless of equal visual sector size. The selection is never decided by the GIF.
- Timing: spinner animation ~5.94 sec; separate Telegram reveal after 7.5 sec, never the caption.
- No real cards/ledgers/rewards in this test.
