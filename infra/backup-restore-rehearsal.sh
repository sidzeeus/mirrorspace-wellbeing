#!/usr/bin/env sh
# Backup and restore rehearsal against the local compose stack.
#
#   sh infra/backup-restore-rehearsal.sh
#
# It takes a real backup of the development database, restores it into a separate
# scratch database, checks that every table has the same number of rows, checks that
# an encrypted field can still be read with the application's keys, and drops the
# scratch database. It never touches the original data. The dump file is written to a
# temporary directory and deleted at the end: a dump contains personal data and must
# never be committed or left lying around.
set -eu

SCRATCH_DB=restore_rehearsal
DUMP="$(mktemp -d)/wellbeing.dump"
trap 'rm -f "$DUMP"; docker compose exec -T db dropdb -U wellbeing --if-exists "$SCRATCH_DB" >/dev/null 2>&1 || true' EXIT

count_rows() {
  docker compose exec -T db psql -U wellbeing -d "$1" -tA -c "
    SELECT string_agg(format('%s=%s', table_name,
             (xpath('/row/c/text()', query_to_xml(format('select count(*) as c from %I', table_name), false, true, '')))[1]::text),
             ' ' ORDER BY table_name)
    FROM information_schema.tables WHERE table_schema = 'public';"
}

echo "1. Backing up"
docker compose exec -T db pg_dump -U wellbeing --format=custom wellbeing > "$DUMP"
echo "   $(wc -c < "$DUMP") bytes"

echo "2. Restoring into a scratch database"
docker compose exec -T db dropdb -U wellbeing --if-exists "$SCRATCH_DB"
docker compose exec -T db createdb -U wellbeing "$SCRATCH_DB"
docker compose exec -T db pg_restore -U wellbeing --no-owner -d "$SCRATCH_DB" < "$DUMP"

echo "3. Comparing row counts, table by table"
ORIGINAL="$(count_rows wellbeing)"
RESTORED="$(count_rows "$SCRATCH_DB")"
if [ "$ORIGINAL" != "$RESTORED" ]; then
  echo "   MISMATCH"; echo "   original: $ORIGINAL"; echo "   restored: $RESTORED"; exit 1
fi
echo "   identical across $(echo "$ORIGINAL" | wc -w) tables"

echo "4. Reading encrypted fields from the restored copy with the application keys"
docker compose exec -T \
  -e DATABASE_URL="postgres://wellbeing:wellbeing@db:5432/$SCRATCH_DB" \
  web python manage.py shell -c "
from apps.episodes.models import Trigger
from apps.sharing.models import TrustedContact
from apps.safety.models import SafetyPlan
read = [len(t.label) for t in Trigger.objects.all()[:50]]
read += [len(c.email) for c in TrustedContact.objects.all()[:50]]
read += [len(p.warning_signs) for p in SafetyPlan.objects.all()[:50]]
print('   decrypted', len(read), 'encrypted values without error')
" | tail -1

echo "5. Cleaning up (scratch database and dump file are removed)"
echo "Rehearsal passed."
