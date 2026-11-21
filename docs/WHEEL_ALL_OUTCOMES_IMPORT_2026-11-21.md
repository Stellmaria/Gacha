# Gacha issue #16 — import and browser test

- Scope: standalone original `Velvet_wheel_all_outcomes.zip` unpacked under `wheel/` and linked from the Gacha homepage; no bot modifications
- Source SHA256: `ef95e6a1f0fcf5c8ca43091430e5ba5d88d700d6d233a613d864b0b3ce2f4cd2`
- Files: 33 original archive members + `wheel/index.html` identical to original viewer + hash registry + import notes
- Six deterministic videos with separate stops and a self-contained `HTML Canvas` viewer from the archive
- `node --test` and other CI checks must pass before merge; browser navigation/Pages activation separately verified
- No credit or reward changes, no Telegram sends, no Velvet production deployment
