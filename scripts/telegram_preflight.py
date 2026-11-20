#!/usr/bin/env python3
"""Read-only Telegram getMe probe. Never emit the token or full request URL."""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


class ProbeFailure(Exception):
    """Safe-to-display error without credentials or URL."""


def check_bot(token: str, target: str, opener=urlopen) -> str:
    if target not in {"production", "test"}:
        raise ProbeFailure("Invalid bot environment.")
    if not token or not re.fullmatch(r"[0-9]+:[A-Za-z0-9_-]{10,}", token):
        raise ProbeFailure("Bot token is missing or does not match Telegram format.")
    suffix = "/test" if target == "test" else ""
    request = Request(
        f"https://api.telegram.org/bot{token}{suffix}/getMe",
        headers={"User-Agent": "gacha-readonly-preflight/1"},
        method="GET",
    )
    try:
        with opener(request, timeout=12) as response:
            result = json.load(response)
    except HTTPError as exc:
        raise ProbeFailure(
            f"Telegram returned HTTP {exc.code}; verify token and selected environment."
        ) from None
    except (URLError, TimeoutError):
        raise ProbeFailure("Telegram connection timed out or was unavailable.") from None
    except (ValueError, OSError):
        raise ProbeFailure("Telegram response could not be decoded.") from None

    if not isinstance(result, dict) or result.get("ok") is not True:
        raise ProbeFailure("Telegram did not confirm bot authentication.")
    bot = result.get("result")
    if not isinstance(bot, dict) or not isinstance(bot.get("id"), int):
        raise ProbeFailure("Telegram returned an invalid bot identity.")
    username = bot.get("username")
    if not isinstance(username, str) or not re.fullmatch(r"[A-Za-z0-9_]{5,32}", username):
        raise ProbeFailure("Telegram returned an invalid bot username.")
    return username


def main() -> int:
    parser = argparse.ArgumentParser(description="Gacha Bot API read-only connectivity check")
    parser.add_argument("--target", choices=("test", "production"), required=True)
    args = parser.parse_args()
    token = os.environ.get("GACHA_BOT_TOKEN", "")
    try:
        username = check_bot(token, args.target)
    except ProbeFailure as exc:
        # ProbeFailure messages are deliberately sanitized; never print exceptions
        # from urllib/Request, because their URL contains the credential.
        print(f"CHECK FAILED: {exc}", file=sys.stderr)
        return 1
    except Exception:
        print("CHECK FAILED: unexpected error; details suppressed to protect bot token.", file=sys.stderr)
        return 1
    print(f"CHECK OK: @{username} ({args.target} environment, read-only getMe)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
