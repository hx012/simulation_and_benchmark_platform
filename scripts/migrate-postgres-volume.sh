#!/usr/bin/env bash
set -Eeuo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd -- "$SCRIPT_DIR/.." && pwd)"
PLATFORM_ENV_FILE="${PLATFORM_ENV_FILE:-$PROJECT_ROOT/.env.platform}"
DB_CONTAINER=ascend-platform-postgres
DB_VOLUME=ascend-platform-postgres-data
TIMESTAMP="$(date -u +%Y%m%dT%H%M%SZ)"
BACKUP_DIR="$PROJECT_ROOT/runtime/backups/postgres/$TIMESTAMP"
BACKUP_FILE="$BACKUP_DIR/ascend_platform.dump"
LEGACY_CONTAINER="${DB_CONTAINER}-legacy-${TIMESTAMP}"

old_renamed=0
migration_complete=0

info() {
  printf '[db-migration] %s\n' "$*"
}

fail() {
  printf '[db-migration] ERROR: %s\n' "$*" >&2
  exit 1
}

database_mount_name() {
  docker inspect \
    --format '{{range .Mounts}}{{if eq .Destination "/var/lib/postgresql/data"}}{{.Name}}{{end}}{{end}}' \
    "$1" 2>/dev/null
}

rollback_on_exit() {
  local exit_code=$?
  trap - EXIT
  if [[ "$exit_code" == 0 || "$migration_complete" == 1 ]]; then
    exit "$exit_code"
  fi

  printf '[db-migration] Migration failed; restoring the legacy container.\n' >&2
  if [[ "$old_renamed" == 1 ]]; then
    if docker inspect "$DB_CONTAINER" >/dev/null 2>&1; then
      docker rm -f "$DB_CONTAINER" >/dev/null 2>&1 || true
    fi
    if docker inspect "$LEGACY_CONTAINER" >/dev/null 2>&1; then
      docker rename "$LEGACY_CONTAINER" "$DB_CONTAINER" >/dev/null
      docker start "$DB_CONTAINER" >/dev/null
      printf '[db-migration] Original database container is running again; application processes remain stopped.\n' >&2
    fi
  fi
  if [[ -f "$BACKUP_FILE" ]]; then
    printf '[db-migration] Backup retained at %s\n' "$BACKUP_FILE" >&2
  fi
  exit "$exit_code"
}

trap rollback_on_exit EXIT

command -v docker >/dev/null 2>&1 || fail "Docker is required."
docker info >/dev/null 2>&1 || fail "Docker daemon is not available."
docker compose version >/dev/null 2>&1 || fail "Docker Compose plugin is not available."
[[ -f "$PLATFORM_ENV_FILE" ]] || fail "Missing $PLATFORM_ENV_FILE."

set -a
# shellcheck disable=SC1090
source "$PLATFORM_ENV_FILE"
set +a
: "${POSTGRES_USER:=ascend_platform}"
: "${POSTGRES_PASSWORD:?POSTGRES_PASSWORD is required in $PLATFORM_ENV_FILE}"
: "${POSTGRES_DB:=ascend_platform}"
: "${POSTGRES_PORT:=15432}"
export POSTGRES_USER POSTGRES_PASSWORD POSTGRES_DB POSTGRES_PORT

docker inspect "$DB_CONTAINER" >/dev/null 2>&1 || fail "Container $DB_CONTAINER does not exist."
current_mount="$(database_mount_name "$DB_CONTAINER")"
if [[ "$current_mount" == "$DB_VOLUME" ]]; then
  info "Database already uses $DB_VOLUME; no migration is needed."
  migration_complete=1
  exit 0
fi
[[ -n "$current_mount" ]] || fail "Cannot identify the current PostgreSQL data mount."
if docker volume inspect "$DB_VOLUME" >/dev/null 2>&1; then
  fail "Target volume $DB_VOLUME already exists. Inspect it before retrying; it will not be overwritten."
fi

docker start "$DB_CONTAINER" >/dev/null
current_user="$(docker exec "$DB_CONTAINER" printenv POSTGRES_USER)"
current_database="$(docker exec "$DB_CONTAINER" printenv POSTGRES_DB)"

for attempt in {1..60}; do
  if docker exec "$DB_CONTAINER" pg_isready -U "$current_user" -d "$current_database" >/dev/null 2>&1; then
    break
  fi
  sleep 1
done
docker exec "$DB_CONTAINER" pg_isready -U "$current_user" -d "$current_database" >/dev/null

"$SCRIPT_DIR/platform.sh" stop-apps
if pgrep -f 'uvicorn app[.]main:app|worker/simulation_worker[.]py' >/dev/null 2>&1; then
  fail "Unmanaged Backend or Worker processes are still running. Stop them before migration."
fi

mkdir -p "$BACKUP_DIR"
info "Creating logical backup from volume $current_mount..."
docker exec "$DB_CONTAINER" \
  pg_dump -U "$current_user" -d "$current_database" --format=custom --no-owner \
  >"$BACKUP_FILE"
[[ -s "$BACKUP_FILE" ]] || fail "Database backup is empty."

if docker exec "$DB_CONTAINER" \
  psql -U "$current_user" -d "$current_database" -Atqc \
  "SELECT to_regclass('public.simulation_tasks');" | grep -q simulation_tasks; then
  tasks_before="$(docker exec "$DB_CONTAINER" \
    psql -U "$current_user" -d "$current_database" -Atqc \
    'SELECT count(*) FROM simulation_tasks;')"
else
  tasks_before=0
fi
info "Migration snapshot contains $tasks_before simulation task(s)."

docker stop --time 30 "$DB_CONTAINER" >/dev/null
docker rename "$DB_CONTAINER" "$LEGACY_CONTAINER"
old_renamed=1
docker volume create "$DB_VOLUME" >/dev/null

info "Creating PostgreSQL with named volume $DB_VOLUME..."
docker compose \
  --project-directory "$PROJECT_ROOT" \
  --env-file "$PLATFORM_ENV_FILE" \
  -f "$PROJECT_ROOT/compose.yaml" \
  up -d postgres

for attempt in {1..60}; do
  if docker exec "$DB_CONTAINER" pg_isready -U "$POSTGRES_USER" -d "$POSTGRES_DB" >/dev/null 2>&1; then
    break
  fi
  sleep 1
done
docker exec "$DB_CONTAINER" pg_isready -U "$POSTGRES_USER" -d "$POSTGRES_DB" >/dev/null

info "Restoring logical backup..."
docker exec -i "$DB_CONTAINER" \
  pg_restore -U "$POSTGRES_USER" -d "$POSTGRES_DB" \
  --clean --if-exists --no-owner --no-privileges \
  <"$BACKUP_FILE"

tasks_after="$(docker exec "$DB_CONTAINER" \
  psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" -Atqc \
  'SELECT count(*) FROM simulation_tasks;')"
[[ "$tasks_after" == "$tasks_before" ]] || \
  fail "Task count mismatch: before=$tasks_before after=$tasks_after"
[[ "$(database_mount_name "$DB_CONTAINER")" == "$DB_VOLUME" ]] || \
  fail "New container is not mounted to $DB_VOLUME."

migration_complete=1
info "Migration completed successfully."
info "Task count verified: $tasks_after"
info "Backup: $BACKUP_FILE"
info "Rollback container retained (stopped): $LEGACY_CONTAINER"
info "Start the platform with: bash scripts/platform.sh start"
