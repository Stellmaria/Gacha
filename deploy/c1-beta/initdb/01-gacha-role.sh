#!/bin/sh
set -eu
runtime_secret="$(cat /run/secrets/gacha_pg_runtime)"
psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname "$POSTGRES_DB" \
     --set="gacha_runtime_password=$runtime_secret" <<'SQL'
CREATE ROLE gacha_runtime LOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE PASSWORD :'gacha_runtime_password';
ALTER DATABASE gacha_beta OWNER TO gacha_runtime;
SQL
unset runtime_secret
