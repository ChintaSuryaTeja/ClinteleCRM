#!/bin/sh
# Database backups: a compressed pg_dump now, then every 24 hours.
# Keeps the newest 7 in the "backups" volume.
#
#   Run one backup now:   docker compose ... run --rm backup once
#   Restore one:          see the bottom of this file
set -eu

KEEP=7

backup() {
    file="/backups/clientele-$(date -u +%Y%m%d-%H%M%S).sql.gz"
    # Write to a temporary name first, so a half-written file is never mistaken
    # for a good backup.
    pg_dump --no-owner --no-privileges | gzip > "$file.partial"
    mv "$file.partial" "$file"
    echo "backup: wrote $file ($(du -h "$file" | cut -f1))"
    # Delete all but the newest $KEEP.
    # shellcheck disable=SC2012 # our own timestamped names, safe to list with ls
    ls -1t /backups/clientele-*.sql.gz | tail -n +$((KEEP + 1)) | xargs -r rm --
}

if [ "${1:-}" = "once" ]; then
    backup
    exit 0
fi

while :; do
    backup || echo "backup: FAILED" >&2
    sleep 86400
done

# Restore (replaces the current data; stop the app first):
#   docker compose ... stop api worker beat
#   docker compose ... exec -T backup sh -c \
#     'gunzip -c /backups/<file>.sql.gz | psql --single-transaction'
#   docker compose ... start api worker beat
