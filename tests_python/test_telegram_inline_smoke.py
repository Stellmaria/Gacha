"""Offline tests for ordinary-bot manual smoke. Never call real Telegram."""
import io
import json
import unittest
from urllib.error import HTTPError
from unittest.mock import patch

from scripts.telegram_inline_smoke import (
    CALLBACK, DemoError, api, matches_callback, send_gif
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


if __name__ == "__main__":
    unittest.main()
