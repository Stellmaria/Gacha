"""Read-only redacted operator summary of Gacha delivery health.

Never attempts to resend an animation/card, never marks a spin successful, and
never reveals Telegram IDs, private image bytes, player names or tokens.
"""
from __future__ import annotations

from collections import Counter
import json
import os

from gacha_core.beta_preflight import DISALLOWED_DB_NAMES

ALLOWED_STATES=frozenset({'pending','sending','sent','uncertain','failed'})


def delivery_summary(conn, expected_database: str) -> dict:
    if not isinstance(expected_database,str) or not expected_database.startswith('gacha_') or expected_database in DISALLOWED_DB_NAMES:
        raise ValueError('Dedicated Gacha database name required')
    with conn.cursor() as cur:
        cur.execute('SELECT current_database()')
        if cur.fetchone()[0]!=expected_database:
            raise ValueError('Unexpected database identity')
        cur.execute('SELECT state, count(*) FROM gacha.delivery_outbox GROUP BY state')
        counts={state:int(count) for state,count in cur.fetchall()}
        if not set(counts).issubset(ALLOWED_STATES):
            raise ValueError('Unexpected outbox state')
        cur.execute("SELECT count(*) FROM gacha.delivery_outbox WHERE state IN ('uncertain','sending') "
                    "AND updated_at < now() - interval '15 minutes'")
        stale=int(cur.fetchone()[0])
        cur.execute('SELECT count(*) FROM gacha.players')
        players=int(cur.fetchone()[0])
        cur.execute('SELECT count(*) FROM gacha.spins')
        spins=int(cur.fetchone()[0])
    return {'database_verified':True,'counts':{s:counts.get(s,0) for s in sorted(ALLOWED_STATES)},
            'stale_ambiguous_over_15m':stale,'player_count':players,
            'committed_spin_count':spins,'auto_redelivery_enabled':False}


def main() -> int:
    dsn=os.environ.get('GACHA_DATABASE_URL')
    database=os.environ.get('GACHA_EXPECTED_DATABASE_NAME')
    if not dsn or not database:
        print('Gacha reconciliation refused: dedicated database configuration missing')
        return 2
    try:
        import psycopg
        with psycopg.connect(dsn,autocommit=True) as db:
            report=delivery_summary(db,database)
    except Exception:
        print('Gacha reconciliation refused: database inspection failed; details suppressed')
        return 2
    print(json.dumps(report,ensure_ascii=False,sort_keys=True))
    return 0


if __name__=='__main__':
    raise SystemExit(main())
