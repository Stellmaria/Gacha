"""Offline tests for ordinary-bot manual smoke. Never call real Telegram."""
import io
import json
import unittest
from urllib.error import HTTPError
from unittest.mock import patch

from scripts.telegram_inline_smoke import (
    CALLBACK, DemoError, SPINNING_CAPTION, api, deliver_demo_spin, matches_callback, send_gif
)


class InlineDemoTests(unittest.TestCase):
    def test_callback_requires_owner_chat_and_exact_message(self):
        q = {"callback_query": {
            "id": "q1", "data": CALLBACK, "from": {"id": 312},
            "message": {"message_id": 55, "chat": {"id": 312, "type": "private"}}
        }}
        self.assertTrue(matches_callback(q, 312, 312, 55))
        self.assertFalse(matches_callback(q, 312, 313, 55))
        self.assertFalse(matches_callback(q, 312, 312, 56))
        self.assertFalse(matches_callback({"callback_query":{**q["callback_query"], "data":"other"}},312,312,55))

    def test_only_safely_allowlisted_methods_can_be_invoked(self):
        for method in ("sendInvoice", "setWebhook", "deleteMessage", "sendAnimation"):
            with self.subTest(method=method):
                with self.assertRaises(DemoError):
                    api("1:MOCKTOKEN", method, {})

    def test_api_no_secret_in_error_message(self):
        token = "123:TEST_TOKEN_IS_NOT_A_SECRET"
        def bad(request, timeout):
            raise HTTPError(request.full_url, 401, "unauthorized", {}, None)
        with patch("scripts.telegram_inline_smoke.urlopen", bad):
            with self.assertRaises(DemoError) as err:
                api(token, "getUpdates", {})
        self.assertNotIn(token, str(err.exception))

    def test_multipart_sends_only_one_gif_and_expected_caption(self):
        token = "123:TEST_TOKEN_IS_NOT_A_SECRET"
        wire = []
        class FakeResponse:
            def __enter__(self):
                return io.BytesIO(json.dumps({"ok":True, "result":{"message_id":22}}).encode())
            def __exit__(self, *args): pass
        def handle(req, timeout):
            wire.append((req.full_url, req.data))
            return FakeResponse()
        with patch("scripts.telegram_inline_smoke.urlopen", handle):
            sent=send_gif(token, 312, b"GIF89a"+b"placeholder", "Demo test")
        self.assertEqual(sent["message_id"], 22)
        self.assertEqual(len(wire), 1)
        self.assertIn(b'name="animation"; filename="gacha-wheel.gif"', wire[0][1])
        self.assertIn(b"Demo test", wire[0][1])

    def test_reveal_is_separate_and_delayed_beyond_animation(self):
        trace = []
        def fake_media(token, chat_id, data, caption):
            trace.append(("animation", caption))
            return {"message_id": 91}
        def fake_api(token, method, payload):
            trace.append((method, payload["text"]))
            return {"message_id": 92}
        def fake_sleep(seconds):
            trace.append(("delay", seconds))
        with patch("scripts.telegram_inline_smoke.render_ornate_gif",
                   return_value=(b"GIF89a-test", 5.94)), \
             patch("scripts.telegram_inline_smoke.send_gif", fake_media), \
             patch("scripts.telegram_inline_smoke.api", fake_api):
            deliver_demo_spin("fake-token", 312, 4, sleeper=fake_sleep)
        self.assertEqual([x[0] for x in trace], ["animation", "delay", "sendMessage"])
        self.assertGreater(trace[1][1], 5.94)
        self.assertEqual(trace[0][1], SPINNING_CAPTION)
        for label in ("CLASSIC", "ELITE", "ROYAL", "EPIC", "MYTHIC", "ETERNAL",
                      "Выпала", "редкость"):
            self.assertNotIn(label, trace[0][1])
        self.assertIn("MYTHIC", trace[2][1])

    def test_no_reveal_if_animation_delivery_fails(self):
        def fail_media(*args):
            raise DemoError("sendAnimation failed")
        with patch("scripts.telegram_inline_smoke.render_ornate_gif",
                   return_value=(b"GIF89a-test", 5.94)), \
             patch("scripts.telegram_inline_smoke.send_gif", fail_media), \
             patch("scripts.telegram_inline_smoke.api") as bot_api:
            with self.assertRaises(DemoError):
                deliver_demo_spin("fake-token", 312, 0, sleeper=lambda _: None)
            bot_api.assert_not_called()


if __name__ == "__main__":
    unittest.main()
