"""Tiny whitelisted JSON Bot API adapter, no requests until explicitly called."""
from __future__ import annotations

import json
import re
from urllib.request import Request

from scripts.telegram_inline_smoke import DemoError, _read_response

METHODS=frozenset({'getMe','getWebhookInfo','getUpdates','sendMessage',
                   'answerCallbackQuery','editMessageReplyMarkup','editMessageCaption'})


def api(token: str, method: str, payload: dict):
    if method not in METHODS:
        raise DemoError('Telegram method not authorized for Gacha MVP-1')
    if not re.fullmatch(r'\d+:[A-Za-z0-9_-]{10,}',token):
        raise DemoError('Missing or invalid private bot token')
    if not isinstance(payload,dict):
        raise DemoError('Invalid Bot API request payload')
    body=json.dumps(payload,ensure_ascii=False).encode('utf-8')
    req=Request('https://api.telegram.org/bot'+token+'/'+method,
                method='POST',data=body,
                headers={'Content-Type':'application/json'})
    # Network timeout must exceed long-poll timeout to avoid disconnect loops.
    duration=payload.get('timeout',0) if method=='getUpdates' else 0
    timeout=35 if type(duration) is not int else max(35,min(duration+15,80))
    return _read_response(req,timeout=timeout)
