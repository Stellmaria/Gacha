#!/usr/bin/env bash
# Only on GitHub Actions' ephemeral gacha_ci PostgreSQL 18 service.
# This script TRUNCATEs fixture tables and MUST NOT be run on any live database.
set -euo pipefail
if [[ "${GITHUB_ACTIONS:-}" != "true" || "${GACHA_TEST_DATABASE_URL:-}" != "postgresql://gacha_ci:gacha_test_only@localhost:5432/gacha_ci" ]]; then
  echo 'REFUSED: temporary GitHub Actions Gacha CI database only' >&2
  exit 2
fi

# Discover the one PostgreSQL 18 CI service, not a running production database.
mapfile -t containers < <(docker ps --filter 'ancestor=postgres:18' --format '{{.ID}}')
if [[ ${#containers[@]} -ne 1 ]]; then
  echo 'REFUSED: expected one isolated PostgreSQL 18 service' >&2
  exit 2
fi
container="${containers[0]}"

# Create a demonstrative, purely synthetic committed reward and bonus balance.
python - <<'PY'
import os
from datetime import datetime,timezone
from uuid import UUID
import psycopg
from gacha_core import GameCore
uri=os.environ['GACHA_TEST_DATABASE_URL']
with psycopg.connect(uri,autocommit=True) as db:
 name,role=db.execute('SELECT current_database(),current_user').fetchone()
 if (name,role)!=('gacha_ci','gacha_ci'):
  raise SystemExit('REFUSED: not ephemeral gacha_ci')
 db.execute('TRUNCATE gacha.cards,gacha.players RESTART IDENTITY CASCADE')
 db.execute('INSERT INTO gacha.cards (card_id,kind,rarity,title,media_asset_ref,is_active) '
            "VALUES ('backup_classic','standard','Classic','Synthetic CI card','fixture://only',true)")
 game=GameCore(db,rng=lambda upper:0)
 uid=424242
 now=datetime(2026,11,21,20,59,59,tzinfo=timezone.utc)
 game.grant_bonus(uid,UUID('aaaaaaaa-0000-0000-0000-000000000001'),3,'ci-only backup fixture')
 spun=game.spin(uid,UUID('bbbbbbbb-0000-0000-0000-000000000001'),now=now)
 assert spun.card_id=='backup_classic'
 assert game.profile(uid,now=now).daily_remaining==9
 assert game.profile(uid,now=now).bonus_remaining==3
 assert db.execute('SELECT count(*) FROM gacha.spins').fetchone()[0]==1
 print('CI fixture: one committed card and bonus preserved before snapshot')
PY

# All postgres utilities run INSIDE the same ephemeral PG18 service container.
# No host backup paths or personal data, never any production connection.
docker exec "$container" pg_dump -U gacha_ci -d gacha_ci -Fc --file=/tmp/gacha-ci-snapshot.dump
docker exec "$container" createdb -U gacha_ci -O gacha_ci gacha_restore_ci
docker exec "$container" pg_restore -U gacha_ci -d gacha_restore_ci --exit-on-error /tmp/gacha-ci-snapshot.dump

python - <<'PY'
import os
from datetime import datetime, timezone
from uuid import UUID
from urllib.parse import urlsplit,urlunsplit
import psycopg
from gacha_core import GameCore
src=os.environ['GACHA_TEST_DATABASE_URL']
parsed=urlsplit(src)
assert parsed.path=='/gacha_ci'
restored=urlunsplit((parsed.scheme,parsed.netloc,'/gacha_restore_ci',parsed.query,parsed.fragment))
with psycopg.connect(restored,autocommit=True) as db:
 assert db.execute('SELECT current_database()').fetchone()[0]=='gacha_restore_ci'
 assert db.execute('SELECT count(*) FROM gacha.schema_migrations').fetchone()[0]==3
 assert db.execute('SELECT count(*) FROM gacha.cards').fetchone()[0]==1
 assert db.execute('SELECT count(*) FROM gacha.spins').fetchone()[0]==1
 assert db.execute('SELECT count(*) FROM gacha.delivery_outbox').fetchone()[0]==1
 assert db.execute('SELECT quantity FROM gacha.player_cards').fetchone()[0]==1
 core=GameCore(db,rng=lambda upper:0)
 day=datetime(2026,11,21,20,59,59,tzinfo=timezone.utc)
 restored_sp=core.spin(424242,UUID('bbbbbbbb-0000-0000-0000-000000000001'),now=day)
 assert restored_sp.replay and restored_sp.card_id=='backup_classic'
 status=core.profile(424242,now=day)
 assert status.daily_remaining==9 and status.bonus_remaining==3
 assert db.execute('SELECT count(*) FROM gacha.spins').fetchone()[0]==1
 print('PG18 RESTORE DRILL PASS: 3 migrations, player, balance, inventory, outbox, no double charge')
PY

# Ephemeral CI container is automatically destroyed with the job.
