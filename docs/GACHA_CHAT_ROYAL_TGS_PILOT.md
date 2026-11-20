# Royal chat-native UX pilot (manual only)

This is a separate experiment from the previous GIF and WEBM proposals. It follows the owner's approved in-chat storyboard **without Mini Apps or videos**. All media is posted by the existing Telegram test-purpose bot to one explicitly opted-in private chat. It never consumes attempts or creates cards.

## Sequence

1. The bot sends one **static photo** of the previously approved original wheel (first frame of the exact GIF source), with text and a single `Крутить (Royal · демо)` inline button.
2. A valid owner callback is acknowledged immediately and the button is removed (no accidental repeat).
3. The caption becomes `Рубин пробуждается…`. The bot uploads an original **TGS/Lottie animated sticker** showing a jewel-themed spin startup. No external media files or video.
4. The caption becomes `Колесо вращается…`. The bot uploads a second original **TGS/Lottie sticker**: mathematically rotated six-color wheel; pointer and ruby live on a separate non-rotating layer.
5. Only after its nominal playback window does the bot reveal `Выпала редкость: ROYAL` in a separate message.
6. A **clearly labeled placeholder Royal demo card** (no character image, no actual reward) is sent. No character details are invented.

The first pilot is *fixed to Royal* to compare aesthetic and pacing. It is not a probability test and MUST NOT be presented as a real random draw. The existing six-rarity distribution remains untouched in `scripts/telegram_widget_smoke.py` and the production build is untouched.

## Limitations

- Telegram's built-in `sendDice` animations **cannot** be replaced with our own dice type; these are ordinary uploaded TGS stickers arranged to feel like a chat-native ritual.
- TGS is vector animation, not the pixel-exact ornate bitmap. The wheel is **deliberately a simplified, first-pass visual**, not a claim that the owner's portrait design has been recreated. The static cover uses an approved original GIF's first frame only; the full uploaded poster is not yet available as a GitHub asset.
- Animated stickers may loop and don't provide bot-side playback completion callbacks; reveal uses conservative sleeps, so slow client downloads can still cause early text relative to visual playback.
- Telegram text, sticker, and picture messages are separate chat bubbles. The model does **not** claim true internal multi-layer animation inside one Telegram message.
- Manual-only GitHub workflow: `.github/workflows/telegram-chat-royal-pilot.yml`, secret `GACHA_TEST_BOT_TOKEN` (`GACHA_BOT_TOKEN` at execution), concurrent with other Telegram demos via shared concurrency group.
- No other bot accounts, webhook, live service, production deployment, grants, Stars, database, or chargeable actions.
- The run requires one fresh private `/wheel` followed by the demo button press within 80 seconds. Do not dispatch the workflow without the owner deliberately requesting a live test.

## Verification

`python -m unittest tests_python.test_telegram_chat_royal_pilot -v` validates TGS gzip format and limits, separate stationary pointer/core layer, ownership matching, media method restriction, staged delivery, and failure closure. CI checks do not replace an actual Telegram acceptance test.
