# Seven cards · approved private MVP-1 asset catalog

Source: seven exact PNG images supplied directly by the owner in the Gacha project chat. All file bytes were hashed with SHA-256 and PNG sizes verified; the original source images are **not stored in public GitHub**. The separately provided private ZIP is `Gacha_MVP1_7_approved_cards_private.zip` (7 PNGs, `manifest.json`, README). `gacha_core/catalog/approved_cards.json` records exact hashes of all seven originals; any altered bytes or missing cards cause import and image delivery to fail closed.

## Six standard cards available in the daily wheel

| ID | Rarity | Number | Character | Subtitle |
| -- | -- | --: | -- | -- |
| `classic_06_eshmar` | Classic | 06 | Эшмар | Пенная капитуляция |
| `elite_09_tiss` | Elite | 09 | Тисс | Тень цветущих руин |
| `royal_15_odin` | Royal | 15 | Один | Золотой бандит |
| `epic_13_kalli` | Epic | 13 | Калли | Безумие |
| `mythic_17_ellis` | Mythic | 17 | Элис | Искажённое отражение |
| `eternal_21_tiffany` | Eternal | 21 | Тиффани | Кукольный кошмар |

## Separate event

`velvet_22_aydan`: Velvet / #22 / Эйдан / «Кровавый соблазн», `kind=event`, `rarity=NULL`, `drop_key=velvet_event`. It is not eligible for the six-section daily spin. Future event logic requires a separate approval and code path.

## Import (operator only, NO public image upload)

1. Obtain the separate owner-approved ZIP (not part of the public repository), keep it in a controlled location.
2. Choose a `--private-root` **outside the public checkout** with restricted filesystem permissions.
3. `python -m gacha_core.card_store --bundle /secure/Gacha_MVP1_7_approved_cards_private.zip --private-root /secure/gacha-card-assets` installs and checks all seven byte-identical PNGs. This does **not** contact Telegram or PostgreSQL.
4. Against a distinct, already-migrated Gacha database, set `GACHA_DATABASE_URL` securely and repeat with `--register` to activate exactly the seven verified entries. Never supply database URL in source, a command line or public logs. No production DB mutation is authorized by this documentation.
5. For future Telegram delivery, call `image_for_card(private_root, card_id)`, which verifies the original SHA-256 every time and rejects unregistered IDs or modified bytes. Do not build file paths from user-controlled callback data.

Migration `002_card_catalog_metadata.sql` adds `card_number`, `character_name`, `subtitle` and `media_sha256`. Imports are idempotent and reject altered identities. In the absence of the private archive, **no cards are seeded, activated, or issued**. Inventory duplicates remain accounted by `gacha.player_cards.quantity`.

Import readiness is not a claim of a running bot or live delivery. A durable Telegram adapter is tracked separately as #25 and requires a private asset installation and a deployment decision.
