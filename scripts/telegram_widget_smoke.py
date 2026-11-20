#!/usr/bin/env python3
"""Short-lived, manual TEST Bot API demo: no grants, payments or persistent bot."""
from __future__ import annotations

import json
import os
import re
import secrets
import sys
import time
import zlib
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from scripts.telegram_preflight import ProbeFailure, check_bot


class SmokeError(Exception):
    """Safe public error; never include raw URL/token or private chat identity."""


WEIGHTS = (25, 22, 19, 16, 11, 7)
REQUEST_SECONDS = 80


def validate_widget(html: str) -> tuple[int, int]:
    encoded = html.encode("utf-8")
    zipped = zlib.compress(encoded, level=9)
    if not 1 <= len(encoded) <= 32768 or len(zipped) > 4096:
        raise SmokeError("Widget does not fit Telegram HTML / zlib-9 limits.")
    if "TelegramWidget" not in html or "request('spin')" not in html:
        raise SmokeError("Widget missing Telegram callback.")
    if not all(x in html for x in ("25,22,19,16,11,7", "CLASSIC", "ETERNAL")):
        raise SmokeError("Widget probability contract mismatch.")
    return len(encoded), len(zipped)


def choose_rarity(value: int) -> int:
    if not isinstance(value, int) or not 0 <= value < 100:
        raise ValueError("Expected integer between 0 and 99.")
    total = 0
    for i, weight in enumerate(WEIGHTS):
        total += weight
        if value < total:
            return i
    raise RuntimeError("Invalid rarity distribution.")


def choose_owner(updates: list, now: int) -> tuple[int, int]:
    owners: set[tuple[int, int]] = set()
    for item in updates:
        m = item.get("message")
        if not isinstance(m, dict) or m.get("text") != "/wheel":
            continue
        if not isinstance(m.get("date"), int) or not 0 <= now - m["date"] <= 600:
            continue
        chat, user = m.get("chat"), m.get("from")
        if not isinstance(chat, dict) or not isinstance(user, dict):
            continue
        if chat.get("type") == "private" and type(chat.get("id")) is int and chat.get("id") == user.get("id") and user.get("is_bot") is False:
            owners.add((chat["id"], user["id"]))
    if len(owners) != 1:
        raise SmokeError("Expected exactly one recent /wheel in a private Test Server bot chat.")
    return next(iter(owners))


def safe_api(token: str, method: str, payload: dict, timeout: int = 14) -> object:
    url = f"https://api.telegram.org/bot{token}/test/{method}"
    request = Request(url, data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
                      headers={"Content-Type": "application/json"}, method="POST")
    try:
        with urlopen(request, timeout=timeout) as resp:
            raw = json.load(resp)
    except HTTPError as exc:
        # Never print exc, request URL, response, or headers: the URL contains the bot token.
        if exc.code == 409:
            raise SmokeError("Telegram conflict (409): another poller or webhook is active.") from None
        if exc.code == 401:
            raise SmokeError("Telegram rejected TEST bot token (401).") from None
        if exc.code == 400:
            raise SmokeError("Telegram rejected a widget method/HTML (400). See API profile limits.") from None
        raise SmokeError(f"Telegram request failed with HTTP {exc.code}.") from None
    except (URLError, TimeoutError, OSError, ValueError):
        raise SmokeError("Telegram request timed out or response was invalid.") from None
    if not isinstance(raw, dict) or raw.get("ok") is not True:
        raise SmokeError("Telegram rejected the request.")
    return raw.get("result")


def handle_widget_query(item: dict, chat_id: int, user_id: int, message_id: int, result_index: int | None) -> tuple[bool, int | None]:
    q = item.get("widget_query")
    if not isinstance(q, dict):
        return False, result_index
    chat, sender = q.get("chat"), q.get("from")
    if (not isinstance(chat, dict) or not isinstance(sender, dict) or
        chat.get("id") != chat_id or sender.get("id") != user_id or
        q.get("message_id") != message_id or q.get("data") != "spin" or
        not isinstance(q.get("id"), str)):
        return False, result_index
    if result_index is None:
        result_index = choose_rarity(secrets.randbelow(100))
    return True, result_index


def run() -> None:
    token = os.environ.get("GACHA_TEST_BOT_TOKEN", "")
    if not token or not re.fullmatch(r"[0-9]+:[A-Za-z0-9_-]{10,}", token):
        raise SmokeError("GACHA_TEST_BOT_TOKEN is missing or malformed.")
    try:
        check_bot(token, "test")
    except ProbeFailure:
        raise SmokeError("TEST getMe failed. Fix GACHA_TEST_BOT_TOKEN first.") from None

    html = Path("widgets/daily-rarity.html").read_text(encoding="utf-8")
    size, packed = validate_widget(html)
    print(f"Widget HTML validated: {size} UTF-8 bytes; {packed} compressed bytes.")

    # Only an explicit recent command from one private test-server user can receive the widget.
    updates = safe_api(token, "getUpdates", {"timeout": 0, "limit": 100,
                                              "allowed_updates": ["message", "widget_query"]})
    if not isinstance(updates, list):
        raise SmokeError("Telegram did not return an update list.")
    chat_id, user_id = choose_owner(updates, int(time.time()))
    max_update = max((u["update_id"] for u in updates if type(u.get("update_id")) is int), default=-1)
    if max_update < 0:
        raise SmokeError("No valid Telegram update ID.")
    # Acknowledge old test-only updates to avoid re-sending on a second run.
    safe_api(token, "getUpdates", {"offset": max_update + 1, "timeout": 0,
                                   "allowed_updates": ["message", "widget_query"]})

    response = safe_api(token, "sendWidget", {
        "chat_id": chat_id, "html": html, "height": 425, "allow_queries": True,
        "is_shared": False, "caption": "Тест Gacha: реальных наград нет"
    })
    if not isinstance(response, dict) or type(response.get("message_id")) is not int:
        raise SmokeError("Telegram did not return a widget message ID.")
    message_id = response["message_id"]
    print("WIDGET SENT on Telegram Test Server. Tap 'КРУТИТЬ' within 80 seconds.")

    result_index = None
    until = time.monotonic() + REQUEST_SECONDS
    offset = max_update + 1
    while time.monotonic() < until:
        remaining = int(max(1, until - time.monotonic()))
        batch = safe_api(token, "getUpdates", {
            "offset": offset, "timeout": min(8, remaining),
            "allowed_updates": ["message", "widget_query"], "limit": 30
        }, timeout=15)
        if not isinstance(batch, list):
            raise SmokeError("Unexpected polling response.")
        for item in batch:
            if type(item.get("update_id")) is int:
                offset = max(offset, item["update_id"] + 1)
            matched, result_index = handle_widget_query(item, chat_id, user_id, message_id, result_index)
            if not matched:
                continue
            # Answer promptly (<15 seconds). Only this original widget is eligible.
            safe_api(token, "answerWidgetQuery", {
                "widget_query_id": item["widget_query"]["id"],
                "data": json.dumps({"i": result_index})
            })
            safe_api(token, "editMessageWidgetData", {
                "chat_id": chat_id, "message_id": message_id,
                "chat_data": json.dumps({"i": result_index})
            })
            print("WIDGET INTERACTION OK: server-picked demo rarity, state persisted.")
            return
    raise SmokeError("Widget was delivered but no click arrived within 80 seconds; no live interaction verified.")


def main() -> int:
    try:
        run()
        return 0
    except SmokeError as exc:
        print(f"WIDGET SMOKE FAILED: {exc}", file=sys.stderr)
        return 1
    except Exception:
        print("WIDGET SMOKE FAILED: unexpected error (details suppressed to protect credentials).", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
