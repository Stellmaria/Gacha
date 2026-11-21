#!/usr/bin/env bash
set -euo pipefail
umask 077
base=/home/velvet/gacha-beta
cd "$base"
stamp="$(date -u +%Y%m%dT%H%M%SZ)"
target="$base/backups/gacha_$stamp.dump.gpg"
if test -e "$target"; then echo 'Backup name collision, abort'; exit 3; fi
docker compose exec -T postgres pg_dump -U gacha_runtime -d gacha_beta -Fc |
  gpg --batch --yes --pinentry-mode loopback --passphrase-file "$base/secrets/gacha_backup.pass" \
      --symmetric --cipher-algo AES256 --output "$target"
test -s "$target"
chmod 0600 "$target"
echo "GACHA_BACKUP_VERIFIED_ENCRYPTED_FILE $(basename "$target")"
