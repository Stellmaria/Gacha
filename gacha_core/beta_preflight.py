"""Read-only closed-beta readiness checks, fail-closed and privacy-safe.

Importing this module never opens a DB connection, reads secrets or contacts
Telegram. The CLI requires explicit --online for authenticated Bot API checks.
"""
from __future__ import annotations

import argparse
from dataclasses import dataclass
import json
import os
from pathlib import Path
from typing import Any

from gacha_core.card_store import approved_cards, verify_private_cards, CardAssetError
from scripts.telegram_wheel6_smoke import verify_original_assets

REQUIRED_MIGRATIONS = (
    '001_mvp1_core.sql',
    '002_card_catalog_metadata.sql',
    '003_telegram_adapter.sql',
)
DISALLOWED_DB_NAMES = frozenset(('postgres','velvet','diamond','template0','template1'))


@dataclass(frozen=True)
class Check:
    name: str
    ok: bool
    detail: str

    def as_dict(self) -> dict[str, object]:
        return {'name': self.name, 'ok': self.ok, 'detail': self.detail}


def offline_assets_check(private_root: str | Path | None) -> tuple[Check, ...]:
    checks: list[Check] = []
    try:
        verify_original_assets()
    except Exception:
        checks.append(Check('approved_wheel',False,'One or more original MP4/cover files failed verification'))
    else:
        checks.append(Check('approved_wheel',True,'Six wheel MP4 originals and cover verified'))
    try:
        if private_root is None:
            raise CardAssetError('No private storage configured')
        cards=verify_private_cards(private_root)
        if len(cards)!=7:
            raise CardAssetError('Incomplete original cards')
    except (CardAssetError,OSError,ValueError):
        checks.append(Check('private_cards',False,'Exact seven approved PNG originals unavailable or altered'))
    else:
        checks.append(Check('private_cards',True,'Seven approved private PNG hashes verified; event card isolated'))
    return tuple(checks)


def check_database(conn, expected_database: str) -> tuple[Check, ...]:
    """Never writes or locks rows. Return non-sensitive readiness findings."""
    if (not isinstance(expected_database,str) or not expected_database.startswith('gacha_')
            or expected_database in DISALLOWED_DB_NAMES):
        raise ValueError('Expected isolated Gacha database name')
    checks=[]
    with conn.cursor() as cur:
        cur.execute('SELECT current_database(), current_user, current_setting(%s)::integer',
                    ('server_version_num',))
        name,role,pg_version=cur.fetchone()
        checks.append(Check('database_identity',name==expected_database,
                            'Dedicated database matches configured name' if name==expected_database
                            else 'Database identity mismatch'))
        checks.append(Check('pg18',pg_version>=180000,
                            'PostgreSQL 18 or newer' if pg_version>=180000
                            else 'PostgreSQL 18 required for beta acceptance'))
        cur.execute('SELECT rolsuper, rolcreaterole, rolcreatedb FROM pg_roles WHERE rolname=%s',
                    (role,))
        privileges=cur.fetchone()
        restricted=(privileges is not None and not any(privileges))
        checks.append(Check('least_privilege',restricted,
                            'Database role has no superuser, create-role or create-db powers'
                            if restricted else 'Database role exceeds approved beta privileges'))
        cur.execute('SELECT to_regclass(%s)',('gacha.schema_migrations',))
        if cur.fetchone()[0] is None:
            return tuple(checks+[Check('migrations',False,'Gacha migrations not installed'),
                                 Check('card_registry',False,'Card catalog not installed'),
                                 Check('delivery_outbox',False,'No outbox schema')])
        cur.execute('SELECT version FROM gacha.schema_migrations')
        versions={row[0] for row in cur.fetchall()}
        version_ok=set(REQUIRED_MIGRATIONS).issubset(versions)
        checks.append(Check('migrations',version_ok,
                            'MVP-1 migrations present' if version_ok
                            else 'MVP-1 migration(s) missing'))
        if not version_ok:
            return tuple(checks+[Check('card_registry',False,'Card registry cannot be verified'),
                                 Check('delivery_outbox',False,'Delivery journal cannot be verified')])
        cur.execute('SELECT card_id, kind, rarity, drop_key, title, card_number, '
                    'character_name, subtitle, media_sha256, is_active FROM gacha.cards '
                    'ORDER BY card_id')
        rows=cur.fetchall()
        found={row[0]:row[1:] for row in rows}
        cards=approved_cards()
        expected={c['card_id']:(c['kind'],c['rarity'],c['drop_key'],c['title'],c['number'],
                                c['character'],c['subtitle'],c['sha256'],True) for c in cards}
        valid=all(found.get(cid)==value for cid,value in expected.items())
        if valid:
            # Extra active cards cannot be silently injected into the initial beta drop.
            valid=all(not row[-1] or row[0] in expected for row in rows)
        checks.append(Check('card_registry',valid,
                            'Exact approved seven card records active; Velvet only event'
                            if valid else 'Catalog differs from approved private originals'))
        cur.execute('SELECT state, count(*) FROM gacha.delivery_outbox GROUP BY state')
        status=dict(cur.fetchall())
        uncertain=int(status.get('uncertain',0))+int(status.get('sending',0))
        checks.append(Check('delivery_outbox',uncertain==0,
                            'No unresolved ambiguous sends' if uncertain==0
                            else 'Unresolved sends require operator reconciliation'))
    return tuple(checks)


def check_telegram(token: str, expected_username: str) -> tuple[Check, ...]:
    """Only getMe/getWebhookInfo (read-only); no getUpdates or button clicks."""
    from gacha_core.telegram_api import api
    checks=[]
    if not expected_username or not expected_username.endswith('_bot'):
        return (Check('bot_identity',False,'Configured bot username is missing or invalid'),)
    try:
        me=api(token,'getMe',{})
        identity=(isinstance(me,dict) and me.get('is_bot') is True
                  and me.get('username') == expected_username)
    except Exception:
        identity=False
    checks.append(Check('bot_identity',identity,
                        'Test bot username matches' if identity else 'Bot identity not confirmed'))
    if not identity:
        return tuple(checks)
    try:
        hook=api(token,'getWebhookInfo',{})
        unused=isinstance(hook,dict) and not hook.get('url')
    except Exception:
        unused=False
    checks.append(Check('webhook_unset',unused,
                        'Webhook not set (other pollers must still be checked separately)'
                        if unused else 'Webhook or Bot API inspection blocks polling'))
    return tuple(checks)


def run_preflight(private_root: str | Path | None, db=None,
                  expected_database: str | None=None, *, online: bool=False,
                  token: str | None=None, username: str | None=None) -> tuple[Check,...]:
    findings=list(offline_assets_check(private_root))
    if db is None or not expected_database:
        findings.append(Check('database',False,'No dedicated Gacha PostgreSQL connection configured'))
    else:
        try:
            findings.extend(check_database(db,expected_database))
        except Exception:
            findings.append(Check('database',False,'Database inspection failed (details suppressed)'))
    if online:
        if not token or not username:
            findings.append(Check('bot_identity',False,'No explicit bot credentials and identity supplied'))
        else:
            findings.extend(check_telegram(token,username))
    else:
        findings.append(Check('telegram_live',False,'Live Bot API preflight not requested'))
    return tuple(findings)


def main() -> int:
    parser=argparse.ArgumentParser(description='Read-only Gacha closed-beta preflight')
    parser.add_argument('--private-root',help='Private seven-original-card directory')
    parser.add_argument('--online',action='store_true',help='Explicitly verify Telegram bot identity/webhook')
    args=parser.parse_args()
    conn=None
    if os.environ.get('GACHA_DATABASE_URL'):
        try:
            import psycopg
            conn=psycopg.connect(os.environ['GACHA_DATABASE_URL'],autocommit=True)
        except Exception:
            conn=None
    try:
        checks=run_preflight(args.private_root or os.environ.get('GACHA_PRIVATE_CARD_ROOT'),
             conn,os.environ.get('GACHA_EXPECTED_DATABASE_NAME'),online=args.online,
             token=os.environ.get('GACHA_BOT_TOKEN'),
             username=os.environ.get('GACHA_EXPECTED_BOT_USERNAME'))
    finally:
        if conn is not None:conn.close()
    print(json.dumps({'ready':all(c.ok for c in checks),
                      'checks':[c.as_dict() for c in checks]},ensure_ascii=False,indent=2))
    return 0 if all(c.ok for c in checks) else 2


if __name__=='__main__':
    raise SystemExit(main())
