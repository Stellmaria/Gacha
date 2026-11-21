#!/usr/bin/env python3
"""Manual-only private Telegram Royal MP4 pilot using the OWNER-APPROVED wheel.

Nothing in this module runs as a service. Only a fresh /royaltest command in
one unambiguous private chat can receive a message. No balances or grants.
"""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import re
import secrets
import sys
import time
from urllib.request import Request

from scripts.telegram_inline_smoke import DemoError, _read_response, api
from scripts.telegram_preflight import ProbeFailure, check_bot

ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / 'wheel' / 'checks' / 'original_sha256.json'
VIDEO = ROOT / 'wheel' / 'videos' / 'Royal.mp4'
COVER = ROOT / 'wheel' / 'source' / 'master.png'
CALLBACK = 'gacha:approved:royal:mp4:v1'
COMMAND = '/royaltest'
POLL_SECONDS = 90
VIDEO_SECONDS = 10.4
REVEAL_DELAY_SECONDS = 12.0
CAPTION = 'Колесо вращается…\nVelvet Gacha · демонстрация без выдачи карт и списаний.'
COVER_CAPTION = ('Velvet Gacha · колесо судьбы\n\n'
                 'Проверяем утверждённое вращение Royal прямо в Telegram.\n'
                 'Только визуальное демо: карт и попыток не начисляем.')
RESULT_TEXT = '✦ ROYAL ✦\nКолесо остановилось!\nДЕМО: настоящую карту не выдавали, попытку не списывали.'


def load_approved_media() -> tuple[bytes, bytes]:
    """Fail closed if assets are replaced or changed after owner's approval."""
    manifest = json.loads(MANIFEST.read_text(encoding='utf-8'))
    data = []
    for filename, path, maximum, signature in (
        ('source/master.png', COVER, 10_000_000, b'\x89PNG\r\n\x1a\n'),
        ('videos/Royal.mp4', VIDEO, 50_000_000, b'ftyp'),
    ):
        raw = path.read_bytes()
        expected_sha = manifest.get(filename)
        signature_ok = raw.startswith(signature) if filename.endswith('.png') else raw[4:8] == signature
        if (not isinstance(expected_sha, str) or
            hashlib.sha256(raw).hexdigest() != expected_sha or
            len(raw) > maximum or not signature_ok):
            raise DemoError('Approved image/video missing, modified or too large.')
        data.append(raw)
    return data[0], data[1]


def select_owner(updates: list[dict], now: int) -> tuple[int, int]:
    """A fresh exact command, same user and private chat; no group or bots."""
    owners: set[tuple[int, int]] = set()
    for update in updates:
        message = update.get('message')
        if not isinstance(message, dict) or message.get('text') != COMMAND:
            continue
        timestamp = message.get('date')
        sender, chat = message.get('from'), message.get('chat')
        if (type(timestamp) is not int or not 0 <= now - timestamp <= 300 or
            not isinstance(sender, dict) or not isinstance(chat, dict) or
            sender.get('is_bot') is not False or chat.get('type') != 'private' or
            type(chat.get('id')) is not int or chat.get('id') != sender.get('id')):
            continue
        owners.add((chat['id'], sender['id']))
    if len(owners) != 1:
        raise DemoError('Exactly one recent private /royaltest sender is required.')
    return next(iter(owners))


def matches_callback(update: dict, chat_id: int, user_id: int, cover_mid: int) -> bool:
    query = update.get('callback_query')
    if not isinstance(query, dict) or query.get('data') != CALLBACK or not query.get('id') or not isinstance(query['id'], str):
        return False
    sender, message = query.get('from'), query.get('message')
    if not isinstance(sender, dict) or not isinstance(message, dict):
        return False
    chat = message.get('chat')
    return bool(isinstance(chat, dict) and sender.get('id') == user_id == chat_id
                and chat.get('id') == chat_id and chat.get('type') == 'private'
                and message.get('message_id') == cover_mid)


def send_media(token: str, chat_id: int, method: str, raw: bytes, caption: str,
               *, reply_markup: dict | None = None) -> dict:
    """Whitelisted multipart upload; no URL/token appears in errors/logs."""
    if method == 'sendPhoto':
        field, filename, mime, maxbytes = 'photo', 'velvet-wheel-master.png', 'image/png', 10_000_000
        if not raw.startswith(b'\x89PNG\r\n\x1a\n'):
            raise DemoError('Invalid PNG cover.')
    elif method == 'sendAnimation':
        field, filename, mime, maxbytes = 'animation', 'velvet-wheel-royal.mp4', 'video/mp4', 50_000_000
        if raw[4:8] != b'ftyp':
            raise DemoError('Invalid MP4 file.')
    else:
        raise DemoError('Forbidden media method.')
    if not raw or len(raw) > maxbytes:
        raise DemoError('Media size invalid.')
    boundary = 'gacha_' + secrets.token_hex(12)
    fields = {'chat_id': str(chat_id), 'caption': caption}
    if method == 'sendAnimation':
        fields.update({'duration': '11', 'width': '720', 'height': '960'})
    if reply_markup is not None:
        fields['reply_markup'] = json.dumps(reply_markup, ensure_ascii=False)
    payload = []
    for key, value in fields.items():
        payload.append(('--' + boundary + '\r\nContent-Disposition: form-data; name="' + key + '"\r\n\r\n' + value + '\r\n').encode('utf-8'))
    payload.append(('--' + boundary + '\r\nContent-Disposition: form-data; name="' + field + '"; filename="' + filename + '"\r\nContent-Type: ' + mime + '\r\n\r\n').encode('utf-8'))
    payload.extend((raw, ('\r\n--' + boundary + '--\r\n').encode('ascii')))
    req = Request('https://api.telegram.org/bot' + token + '/' + method, method='POST',
                  data=b''.join(payload),
                  headers={'Content-Type': 'multipart/form-data; boundary=' + boundary})
    result = _read_response(req, timeout=50)
    if not isinstance(result, dict) or type(result.get('message_id')) is not int:
        raise DemoError('Telegram did not acknowledge the media message.')
    if method == 'sendAnimation' and not isinstance(result.get('animation'), dict):
        raise DemoError('Telegram did not return an animation object.')
    return result


def deliver_royal(token: str, chat_id: int, video: bytes, *, sleeper=time.sleep) -> None:
    """One exact approved Royal MP4, then server-announced demo outcome."""
    send_media(token, chat_id, 'sendAnimation', video, CAPTION)
    sleeper(REVEAL_DELAY_SECONDS)
    result = api(token, 'sendMessage', {'chat_id': chat_id, 'text': RESULT_TEXT})
    if not isinstance(result, dict) or type(result.get('message_id')) is not int:
        raise DemoError('Telegram did not acknowledge the reveal message.')


def run() -> None:
    token = os.environ.get('GACHA_BOT_TOKEN', '')
    if not re.fullmatch(r'[0-9]+:[A-Za-z0-9_-]{10,}', token):
        raise DemoError('GACHA_BOT_TOKEN secret is missing or malformed.')
    cover, video = load_approved_media()
    try:
        check_bot(token, 'production')
    except ProbeFailure:
        raise DemoError('Telegram ordinary bot getMe preflight failed.') from None
    updates = api(token, 'getUpdates', {
        'timeout': 0, 'limit': 100, 'allowed_updates': ['message', 'callback_query']
    })
    if not isinstance(updates, list):
        raise DemoError('Telegram updates response was not a list.')
    chat_id, user_id = select_owner(updates, int(time.time()))
    offset = max((u['update_id'] for u in updates if type(u.get('update_id')) is int), default=-1) + 1
    if offset <= 0:
        raise DemoError('Telegram updates offset missing.')
    api(token, 'getUpdates', {'offset': offset, 'timeout': 0,
                              'allowed_updates': ['message', 'callback_query']})
    cover_result = send_media(token, chat_id, 'sendPhoto', cover, COVER_CAPTION,
                              reply_markup={'inline_keyboard': [[{
                                  'text': '✦ Крутить Royal · тест', 'callback_data': CALLBACK
                              }]]})
    cover_mid = cover_result['message_id']
    print('ROYAL MP4 PILOT: cover delivered, waiting for a single owner click.')
    deadline = time.monotonic() + POLL_SECONDS
    while time.monotonic() < deadline:
        remaining = max(1, int(deadline - time.monotonic()))
        batch = api(token, 'getUpdates', {
            'offset': offset, 'timeout': min(8, remaining), 'limit': 50,
            'allowed_updates': ['message', 'callback_query']
        })
        if not isinstance(batch, list):
            raise DemoError('Unexpected callback response.')
        for update in batch:
            if type(update.get('update_id')) is int:
                offset = max(offset, update['update_id'] + 1)
            if not matches_callback(update, chat_id, user_id, cover_mid):
                continue
            qid = update['callback_query']['id']
            api(token, 'answerCallbackQuery', {
                'callback_query_id': qid, 'text': 'Запускаю оригинальное колесо…', 'show_alert': False
            })
            # Disable the button before sending media, so double-clicks never charge/replay.
            api(token, 'editMessageReplyMarkup', {
                'chat_id': chat_id, 'message_id': cover_mid, 'reply_markup': {'inline_keyboard': []}
            })
            deliver_royal(token, chat_id, video)
            print('ROYAL MP4 PILOT SUCCESS: approved MP4 and delayed demo reveal acknowledged.')
            return
    raise DemoError('The single Royal button was not clicked within the 90 second window.')


def main() -> int:
    try:
        run()
        return 0
    except DemoError as exc:
        print('ROYAL MP4 PILOT FAILED: ' + str(exc), file=sys.stderr)
        return 1
    except Exception:
        print('ROYAL MP4 PILOT FAILED: unexpected error; private details suppressed.', file=sys.stderr)
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
