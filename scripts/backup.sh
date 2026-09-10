#!/bin/sh
# Database backup (a bind-mounted volume is NOT a backup — this is). Run from the project folder:
#   sh scripts/backup.sh            -> data/backups/memboy_YYYYmmdd_HHMM.sql.gz  (keeps the last 14)
# Restore into an empty db:  gunzip -c data/backups/<file> | docker compose exec -T db psql -U memboy -d memboy
set -e
mkdir -p data/backups
out="data/backups/memboy_$(date +%Y%m%d_%H%M).sql.gz"
docker compose exec -T db pg_dump -U memboy --no-owner --no-privileges memboy | gzip > "$out"
ls -t data/backups/memboy_*.sql.gz | tail -n +15 | xargs -r rm --
echo "wrote $out ($(du -h "$out" | cut -f1)); uploads/reports live in ./data — include that folder in any off-machine copy"
