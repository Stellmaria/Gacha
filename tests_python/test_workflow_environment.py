"""Offline contract: test-purpose bot uses the correct Telegram environment."""
from pathlib import Path
import unittest


class WorkflowEnvironmentTests(unittest.TestCase):
    def test_preflight_distinguishes_purpose_from_dedicated_server(self):
        wf = Path(".github/workflows/telegram-preflight.yml").read_text(encoding="utf-8")
        self.assertIn("default: existing-test-bot", wf)
        self.assertIn("inputs.target == 'telegram-test-server'", wf)
        self.assertIn("inputs.target == 'existing-test-bot'", wf)
        self.assertIn("GACHA_TEST_BOT_TOKEN", wf)
        self.assertIn("python3 scripts/telegram_preflight.py --target test", wf)
        self.assertIn("python3 scripts/telegram_preflight.py --target production", wf)
        self.assertNotIn("  push:", wf)
        self.assertNotIn("  pull_request:", wf)

    def test_manual_gif_uses_existing_bot_secret_not_separate_production_bot(self):
        wf = Path(".github/workflows/telegram-inline-smoke.yml").read_text(encoding="utf-8")
        self.assertIn("secrets.GACHA_TEST_BOT_TOKEN", wf)
        self.assertNotIn("secrets.GACHA_BOT_TOKEN", wf)
        self.assertIn("workflow_dispatch:", wf)
        self.assertNotIn("  push:", wf)
        self.assertNotIn("  pull_request:", wf)


if __name__ == "__main__":
    unittest.main()
