"""Offline-only tests. All credentials are fictional, all requests are mocked."""
import io
import unittest
from urllib.error import HTTPError, URLError

from scripts.telegram_preflight import ProbeFailure, check_bot, diagnose_test_token


TOKEN = "1234567890:NOTAREALTOKENFORUNITTESTS"


class MemoryResponse:
    def __init__(self, payload):
        self.stream = io.BytesIO(payload)

    def __enter__(self):
        return self.stream

    def __exit__(self, exc_type, exc, tb):
        self.stream.close()


class TelegramPreflightTests(unittest.TestCase):
    def test_production_url_and_no_side_effects(self):
        sent = []
        def opener(request, timeout):
            sent.append((request.full_url, request.get_method(), timeout))
            return MemoryResponse(b'{"ok": true, "result": {"id": 22, "username": "GachaTestBot"}}')
        self.assertEqual(check_bot(TOKEN, "production", opener), "GachaTestBot")
        self.assertEqual(sent, [(f"https://api.telegram.org/bot{TOKEN}/getMe", "GET", 12)])

    def test_test_server_url(self):
        sent = []
        def opener(request, timeout):
            sent.append(request.full_url)
            return MemoryResponse(b'{"ok":true,"result":{"id":2,"username":"TestGachaBot"}}')
        self.assertEqual(check_bot(TOKEN, "test", opener), "TestGachaBot")
        self.assertEqual(sent, [f"https://api.telegram.org/bot{TOKEN}/test/getMe"])

    def test_missing_secret_fails_without_network(self):
        for missing in ["", "bad-token", "000:tiny"]:
            with self.subTest(missing=missing):
                with self.assertRaises(ProbeFailure):
                    check_bot(missing, "test", lambda *_args, **_kwargs: self.fail("should not call network"))

    def test_http_error_never_exposes_secret(self):
        def fail(request, timeout):
            raise HTTPError(request.full_url, 401, "unauthorized", {}, None)
        with self.assertRaises(ProbeFailure) as caught:
            check_bot(TOKEN, "production", fail)
        self.assertNotIn(TOKEN, str(caught.exception))
        self.assertIn("401", str(caught.exception))

    def test_network_error_is_sanitized(self):
        def fail(request, timeout):
            raise URLError(f"failed URL: {request.full_url}")
        with self.assertRaises(ProbeFailure) as caught:
            check_bot(TOKEN, "test", fail)
        self.assertNotIn(TOKEN, str(caught.exception))

    def test_bad_bot_identity_is_rejected(self):
        def bad(request, timeout):
            return MemoryResponse(b'{"ok":true,"result":{"username":"NoIdBot"}}')
        with self.assertRaises(ProbeFailure):
            check_bot(TOKEN, "production", bad)

    def test_environment_autodetection_without_secret_exposure(self):
        calls = []
        def opener(request, timeout):
            calls.append(request.full_url)
            if '/test/getMe' in request.full_url:
                raise HTTPError(request.full_url, 401, 'bad token', {}, None)
            return MemoryResponse(b'{"ok": true, "result": {"id": 20, "username": "OrdinaryBot"}}')
        self.assertEqual(diagnose_test_token(TOKEN, opener), ('production_only', 'OrdinaryBot'))
        self.assertEqual(len(calls), 2)

    def test_autodetection_does_not_guess_on_network_failure(self):
        def fail(request, timeout):
            raise URLError(request.full_url)
        with self.assertRaises(ProbeFailure):
            diagnose_test_token(TOKEN, fail)

    def test_autodetection_invalid_on_two_401(self):
        def fail(request, timeout):
            raise HTTPError(request.full_url, 401, 'no', {}, None)
        self.assertEqual(diagnose_test_token(TOKEN, fail), ('invalid', None))


if __name__ == "__main__":
    unittest.main()
