"""Explicit versioned PostgreSQL migration; no automatic changes on import.

Set GACHA_DATABASE_URL for a dedicated Gacha database before running.
"""
from __future__ import annotations

import os
from pathlib import Path

MIGRATIONS = Path(__file__).resolve().parents[1] / 'db/migrations'


def apply_migrations(conn) -> None:
    conn.execute('CREATE SCHEMA IF NOT EXISTS gacha')
    conn.execute('CREATE TABLE IF NOT EXISTS gacha.schema_migrations '
                 '(version text PRIMARY KEY, applied_at timestamptz NOT NULL DEFAULT now())')
    for path in sorted(MIGRATIONS.glob('[0-9][0-9][0-9]_*.sql')):
        name = path.name
        with conn.transaction():
            exists = conn.execute('SELECT 1 FROM gacha.schema_migrations WHERE version = %s', (name,)).fetchone()
            if exists:
                continue
            sql = path.read_text(encoding='utf-8').strip()
            if not sql.startswith('BEGIN;') or not sql.endswith('COMMIT;'):
                raise RuntimeError('Migration must be transaction-wrapped')
            sql = sql[len('BEGIN;'):-len('COMMIT;')].strip()
            conn.execute(sql, prepare=False)
            conn.execute('INSERT INTO gacha.schema_migrations (version) VALUES (%s)', (name,))


def main() -> None:
    target = os.environ.get('GACHA_DATABASE_URL')
    if not target:
        raise SystemExit('GACHA_DATABASE_URL is required; no changes made')
    import psycopg
    with psycopg.connect(target, autocommit=True) as db:
        apply_migrations(db)
    print('Gacha MVP-1 migrations applied to configured database.')


if __name__ == '__main__':
    main()
