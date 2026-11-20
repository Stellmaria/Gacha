#!/usr/bin/env python3
"""Manual-only ordinary Telegram demo; no wallet, accounts or persistent service."""
from __future__ import annotations

import io
import json
import os
import re
import secrets
import sys
import time
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from scripts.telegram_preflight import ProbeFailure, check_bot
from scripts.telegram_widget_smoke import choose_owner, choose_rarity
from scripts.wheel_gif import NAMES
from scripts.ornate_wheel import REVEAL_DELAY_SECONDS, render_ornate_gif


class DemoError(Exception):
    """Sanitized error; do not print credential-bearing HTTP errors."""


CALLBACK = "gacha:demo:spin:v1"
POLL_SECONDS = 80
SPINNING_CAPTION = "Колесо вращается…\\nДЕМО: карточки и попытки не начисляются."
ALLOWED_METHODS = frozenset({
    "getUpdates", "sendMessage", "answerCallbackQuery",
    "editMessageReplyMarkup", "sendAnimation",
})


def _read_response(req: Request, timeout: int = 15):
    try:
        with urlopen(req, timeout=timeout) as response:
            payload = json.load(response)
    except HTTPError as exc:
        if exc.code == 401:
            raise DemoError("Ordinary bot token rejected (HTTP 401).") from None
        if exc.code == 409:
            raise DemoError("Bot webhook or another getUpdates poller is active (HTTP 409).") from None
        raise DemoError(f"Telegram API returned HTTP {exc.code}.") from None
    except (URLError, TimeoutError, OSError, ValueError):
        raise DemoError("Telegram API request failed; network or response error.") from None
    if not isinstance(payload, dict) or payload.get("ok") is not True:
        raise DemoError("Telegram API request was rejected.")
    return payload.get("result")


def api(token: str, method: str, data: dict):
    if method not in ALLOWED_METHODS - {"sendAnimation"}:
        raise DemoError("Forbidden Telegram method.")
    url = f"https://api.telegram.org/bot{token}/{method}"
    request = Request(url, method="POST",
                      data=json.dumps(data, ensure_ascii=False).encode("utf-8"),
                      headers={"Content-Type": "application/json"})
    return _read_response(request)


def send_gif(token: str, chat_id: int, gif: bytes, caption: str):
    """Multipart sendAnimation with in-memory GIF and no token leakage."""
    if not gif.startswith(b"GIF89a") or len(gif) > 8_000_000:
        raise DemoError("GIF rendering produced invalid or excessive animation.")
    boundary = "gacha_" + secrets.token_hex(12)
    pieces = []
    for name, value in (("chat_id", str(chat_id)), ("caption", caption)):
        pieces.append(("--"+boundary+"\r\n"+'Content-Disposition: form-data; name="'+name+'"\r\n\r\n'+value+"\r\n").encode("utf-8"))
    pieces.append(("--"+boundary+"\r\n"+'Content-Disposition: form-data; name="animation"; filename="gacha-wheel.gif"\r\nContent-Type: image/gif\r\n\r\n').encode("utf-8"))
    pieces.extend([gif, ("\r\n--"+boundary+"--\r\n").encode("ascii")])
    payload = b"".join(pieces)
    url = f"https://api.telegram.org/bot{token}/sendAnimation"
    request = Request(url, method="POST", data=payload,
                      headers={"Content-Type": "multipart/form-data; boundary=" + boundary})
    return _read_response(request, timeout=20)


def deliver_demo_spin(token: str, chat_id: int, rarity: int, *, sleeper=time.sleep) -> None:
    """Send hidden-outcome animation, then reveal in a separate message.

    The server commits to one picked result before sending the animation.
    A Telegram send acknowledgment is not a client playback acknowledgment;
    the extra delay minimizes, but cannot rule out, early client-side reveals.
    """
    gif, playback_seconds = render_ornate_gif(rarity)
    result = send_gif(token, chat_id, gif, SPINNING_CAPTION)
    if not isinstance(result, dict) or type(result.get("message_id")) is not int:
        raise DemoError("Telegram did not confirm the animation message.")
    sleeper(max(REVEAL_DELAY_SECONDS, playback_seconds + 1))
    revealed = api(token, "sendMessage", {
        "chat_id": chat_id,
        "text": "Выпала редкость: " + NAMES[rarity] +
                "\\nДЕМО: карточка не выдана и попытка не списана."
    })
    if not isinstance(revealed, dict) or type(revealed.get("message_id")) is not int:
        raise DemoError("Telegram did not confirm the separate reveal message.")


def matches_callback(update: dict, chat_id: int, user_id: int, message_id: int) -> bool:
    query = update.get("callback_query")
    if not isinstance(query, dict) or query.get("data") != CALLBACK:
        return False
    who, message = query.get("from"), query.get("message")
    if not isinstance(who, dict) or not isinstance(message, dict):
        return False
    chat = message.get("chat")
    return bool(isinstance(chat, dict)
                and who.get("id") == user_id
                and chat.get("id") == chat_id
                and message.get("message_id") == message_id
                and isinstance(query.get("id"), str) and query["id"])


def run() -> None:
    token = os.environ.get("GACHA_BOT_TOKEN", "")
    if not re.fullmatch(r"[0-9]+:[A-Za-z0-9_-]{10,}", token):
        raise DemoError("GACHA_BOT_TOKEN missing. Set the ordinary bot token in GitHub Secrets.")
    try:
        check_bot(token, "production")
    except ProbeFailure:
        raise DemoError("Ordinary Telegram getMe failed. Verify GACHA_BOT_TOKEN.") from None

    updates = api(token, "getUpdates", {
        "timeout": 0, "limit": 100,
        "allowed_updates": ["message", "callback_query"]
    })
    if not isinstance(updates, list):
        raise DemoError("Unexpected update list.")
    try:
        chat_id, user_id = choose_owner(updates, int(time.time()))
    except Exception:
        raise DemoError("Send one fresh /wheel in a private chat with your ordinary bot. Multiple chat owners are not allowed.") from None
    offset = max((u["update_id"] for u in updates if type(u.get("update_id")) is int), default=-1) + 1
    if offset <= 0:
        raise DemoError("Missing Telegram update sequence.")
    api(token, "getUpdates", {"offset": offset, "timeout": 0,
                              "allowed_updates": ["message", "callback_query"]})

    message = api(token, "sendMessage", {
        "chat_id": chat_id,
        "text": "Колесо ежедневных карт · тестовая крутка\n\n"
                "Classic 25% · Elite 22% · Royal 19% · Epic 16% · Mythic 11% · Eternal 7%\n\n"
                "Никаких настоящих карт, попыток и вельветов не начисляется.",
        "reply_markup": {"inline_keyboard": [[{
            "text": "🎡 Крутить (демо)", "callback_data": CALLBACK
        }]]}
    })
    if not isinstance(message, dict) or type(message.get("message_id")) is not int:
        raise DemoError("Telegram did not return a demo message ID.")
    mid = message["message_id"]
    print("Ordinary Telegram demo button sent. Tap within 80 seconds.")

    until = time.monotonic() + POLL_SECONDS
    while time.monotonic() < until:
        remaining = max(1, int(until - time.monotonic()))
        batch = api(token, "getUpdates", {
            "offset": offset, "timeout": min(8, remaining),
            "limit": 50, "allowed_updates": ["message", "callback_query"]
        })
        if not isinstance(batch, list):
            raise DemoError("Unexpected Telegram callback batch.")
        for update in batch:
            if type(update.get("update_id")) is int:
                offset = max(offset, update["update_id"] + 1)
            if not matches_callback(update, chat_id, user_id, mid):
                continue
            query = update["callback_query"]
            # Respond to Telegram quickly, before rendering any image.
            api(token, "answerCallbackQuery", {
                "callback_query_id": query["id"],
                "text": "Вращаем колесо…",
                "show_alert": False
            })
            # Remove the button even if the later media upload fails.
            api(token, "editMessageReplyMarkup", {
                "chat_id": chat_id, "message_id": mid,
                "reply_markup": {"inline_keyboard": []}
            })
            rarity = choose_rarity(secrets.randbelow(100))
            deliver_demo_spin(token, chat_id, rarity)
            print("DEMO SUCCESS: animation delivered for one server-picked rarity.")
            return
    raise DemoError("Demo button was sent, but no click arrived within 80 seconds.")


def main() -> int:
    try:
        run()
        return 0
    except DemoError as exc:
        print("DEMO FAILED: " + str(exc), file=sys.stderr)
        return 1
    except Exception:
        print("DEMO FAILED: unexpected error; details suppressed to protect credentials.", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
