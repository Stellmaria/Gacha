"""Opt-in single-worker PostgreSQL-backed Telegram poller for Gacha MVP-1.

Never run in GitHub Actions CI, import hooks, production Velvet, or at deploy
without explicit operator permission. Uses the existing Telegram Bot API only
when all required environment gates have been explicitly set.
"""
from __future__ import annotations

import os
from pathlib import Path
import re
import sys
import time

from gacha_core.card_store import verify_private_cards
from gacha_core.telegram_adapter import TelegramClient, TelegramGameAdapter
from gacha_core.telegram_api import api

LOCK_ID = 20261122


def verify_operator_environment(env: dict) -> tuple[str,str,Path,str]:
    if env.get('GACHA_ENABLE_POLLING') != 'YES':
        raise RuntimeError('Persistent bot disabled: explicit GACHA_ENABLE_POLLING=YES required')
    token=env.get('GACHA_BOT_TOKEN','')
    dsn=env.get('GACHA_DATABASE_URL','')
    username=env.get('GACHA_EXPECTED_BOT_USERNAME','')
    root=env.get('GACHA_PRIVATE_CARD_ROOT','')
    if (not re.fullmatch(r'\d+:[a-zA-Z0-9_-]{10,}',token) or
            not dsn or not root or not re.fullmatch(r'[a-zA-Z0-9_]{5,32}',username)):
        raise RuntimeError('Required private Gacha bot/db/cards configuration missing')
    return token,dsn,Path(root),username


def run() -> None:
    token,dsn,root,expected=verify_operator_environment(os.environ)
    # Refuse to start if any of the seven owner-approved originals are missing.
    verify_private_cards(root)
    import psycopg
    db=psycopg.connect(dsn,autocommit=True)
    try:
        if not db.execute('SELECT pg_try_advisory_lock(%s)',(LOCK_ID,)).fetchone()[0]:
            raise RuntimeError('Another Gacha polling worker holds the database singleton lock')
        me=api(token,'getMe',{})
        if not isinstance(me,dict) or me.get('username') != expected:
            raise RuntimeError('Telegram bot identity did not match operator-approved username')
        hook=api(token,'getWebhookInfo',{})
        if not isinstance(hook,dict) or hook.get('url'):
            raise RuntimeError('Webhook already configured; polling would conflict')
        transport=TelegramClient(token)
        handler=TelegramGameAdapter(db,transport,root)
        row=db.execute('SELECT last_update_id FROM gacha.telegram_poll_cursor WHERE singleton=true').fetchone()
        if row is None:
            # First boot: discard pre-existing commands/callbacks instead of
            # unexpectedly running old /spin requests or previous manual demos.
            updates=api(token,'getUpdates',{'limit':100,'timeout':0,
                                            'allowed_updates':['message','callback_query']})
            if not isinstance(updates,list):raise RuntimeError('Telegram history bootstrap failed')
            offset=max((u.get('update_id') for u in updates
                        if type(u.get('update_id')) is int),default=-1)
            db.execute('INSERT INTO gacha.telegram_poll_cursor (singleton,last_update_id) '
                       'VALUES (true,%s)',(offset,))
        else:
            offset=row[0]
        print('Gacha MVP-1 polling active for configured bot; no tokens printed.',flush=True)
        while True:
            updates=api(token,'getUpdates',{'offset':offset+1,'limit':50,'timeout':15,
                                            'allowed_updates':['message','callback_query']})
            if not isinstance(updates,list):raise RuntimeError('Unexpected getUpdates payload')
            for update in updates:
                update_id=update.get('update_id')
                if type(update_id) is not int or update_id<=offset:continue
                # A failed or ambiguous Telegram operation must not cause an
                # automated replay of the same update after a network retry.
                try:
                    handler.handle_update(update)
                except Exception:
                    print('Gacha Telegram update needs operator review; '
                          'details suppressed for privacy.',file=sys.stderr,flush=True)
                offset=update_id
                db.execute('UPDATE gacha.telegram_poll_cursor SET '
                           'last_update_id=%s, updated_at=now() WHERE singleton=true',
                           (offset,))
    finally:
        db.close()


if __name__=='__main__':
    try:
        run()
    except KeyboardInterrupt:
        print('Gacha poller stopped.')
    except Exception:
        print('Gacha poller did not start or stopped; inspect private runtime logs.',file=sys.stderr)
        raise SystemExit(1) from None
