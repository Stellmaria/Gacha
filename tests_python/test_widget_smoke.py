"""Fully offline contract tests; all bot users are fictional."""
import unittest
import time
from pathlib import Path
from scripts.telegram_widget_smoke import WEIGHTS, choose_owner, choose_rarity, handle_widget_query, validate_widget, SmokeError


class WidgetSmokeTests(unittest.TestCase):
    def test_widget_fits_telegram_profile(self):
        content = Path("widgets/daily-rarity.html").read_text(encoding="utf-8")
        raw, compressed = validate_widget(content)
        self.assertLessEqual(raw, 32768)
        self.assertLessEqual(compressed, 4096)
        self.assertEqual(WEIGHTS, (25, 22, 19, 16, 11, 7))

    def test_exact_100_percent_distribution(self):
        actual = [0] * 6
        for i in range(100):
            actual[choose_rarity(i)] += 1
        self.assertEqual(actual, list(WEIGHTS))
        with self.assertRaises(ValueError):
            choose_rarity(100)

    def test_only_recent_unambiguous_private_commands_select_owner(self):
        now = int(time.time())
        valid = {"update_id": 8, "message": {"date": now, "text": "/wheel", "chat": {"id": 112, "type": "private"}, "from": {"id": 112, "is_bot": False}}}
        self.assertEqual(choose_owner([valid], now), (112, 112))
        with self.assertRaises(SmokeError):
            choose_owner([valid, {"update_id": 9, "message": {"date": now, "text": "/wheel", "chat": {"id": 113, "type": "private"}, "from": {"id": 113, "is_bot": False}}}], now)
        with self.assertRaises(SmokeError):
            choose_owner([dict(valid, message=dict(valid["message"], date=now-900))], now)
        with self.assertRaises(SmokeError):
            choose_owner([dict(valid, message=dict(valid["message"], chat={"id":-123, "type":"group"}))], now)

    def test_query_is_bound_to_exact_user_chat_and_widget_message(self):
        q = {"widget_query": {"id": "id1", "chat": {"id": 112}, "from": {"id": 112},
              "message_id": 401, "data": "spin"}}
        ok, idx = handle_widget_query(q, 112, 112, 401, 3)
        self.assertTrue(ok)
        self.assertEqual(idx, 3)
        for changed in [{"chat":{"id":113}}, {"from":{"id":113}}, {"message_id":402},
                        {"data":"unknown"}]:
            bad = {"widget_query": {**q["widget_query"], **changed}}
            matched, result = handle_widget_query(bad, 112, 112, 401, None)
            self.assertFalse(matched)
            self.assertIsNone(result)


if __name__ == "__main__":
    unittest.main()
