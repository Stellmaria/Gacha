"""Closed-beta artifact hashes for the seven temporary Windows test cards.

Metadata only; real PNGs are never committed into the repository.
"""
from unittest import TestCase

from gacha_core.card_store import approved_cards, MANIFEST_PATH


BETA_TEST_ART = {
    "classic_06_eshmar": ("8a8be95c5c2093a1209d3981174b14a0a3f4728a68b5beee4731d6264a608b1f", 2389663),
    "elite_09_tiss": ("0cae1f0800c0f1a585791f35da698d2eec07f1b8f2064bf04f90f37d4ed7354e", 2507450),
    "royal_15_odin": ("3d3f12362354e94f6163d29f6e578588e0aea580e54459c9c9a12ee6ed4a5e1d", 2304266),
    "epic_13_kalli": ("27dce87cf624f8fd1a9af104b5a80fd1918bbd2acca1f2680da174361eca8e54", 2576765),
    "mythic_17_ellis": ("860a4bd25f3858e87a9f0a99775f93dbd10bb8d37b97e94f57a58fe85852aa91", 2860659),
    "eternal_21_tiffany": ("e84968e3eedc4e40e72d751e0554e3aebf0773ffd5aa66e9c6878f5e7cbf0351", 2771864),
    "velvet_22_aydan": ("9d17fadf118a4a32a80f2104253bf6f746d56310e520cefe9bdd5d60a1226c2d", 2491576),
}


class TemporaryBetaArtContract(TestCase):
    def test_test_art_seven_and_no_extra_cards(self):
        import json
        manifest = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
        self.assertIn("temporary closed beta test cards", manifest["bundle_name"])
        cards = approved_cards()
        self.assertEqual({c["card_id"]: (c["sha256"], c["bytes"]) for c in cards}, BETA_TEST_ART)
        self.assertEqual(tuple(c["kind"] for c in cards), ("standard",)*6 + ("event",))
        self.assertEqual(cards[-1]["drop_key"], "velvet_event")
        self.assertIsNone(cards[-1]["rarity"])
