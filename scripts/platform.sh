#!/usr/bin/env bash
set -Eeuo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd -- "$SCRIPT_DIR/.." && pwd)"
BACKEND_DIR="$PROJECT_ROOT/backend"
FRONTEND_DIR="$PROJECT_ROOT/frontend"
BACKEND_VENV="$BACKEND_DIR/.venv"
BACKEND_PYTHON="$BACKEND_VENV/bin/python"
BACKEND_UVICORN="$BACKEND_VENV/bin/uvicorn"
BACKEND_ALEMBIC="$BACKEND_VENV/bin/alembic"
STATE_DIR="$PROJECT_ROOT/runtime/platform"
PID_DIR="$STATE_DIR/pids"
LOG_DIR="$STATE_DIR/logs"
MODE_FILE="$STATE_DIR/mode"
FRONTEND_LOCK_STAMP="$STATE_DIR/frontend-package-lock.sha256"
PLATFORM_ENV_FILE="${PLATFORM_ENV_FILE:-$PROJECT_ROOT/.env.platform}"

DB_CONTAINER=ascend-platform-postgres
DB_VOLUME=ascend-platform-postgres-data

mkdir -p "$PID_DIR" "$LOG_DIR"

usage() {
  cat <<'EOF'
Usage:
  bash scripts/platform.sh setup
  bash scripts/platform.sh update
  bash scripts/platform.sh start [dev|server|static]
  bash scripts/platform.sh stop
  bash scripts/platform.sh stop-apps
  bash scripts/platform.sh restart [dev|server|static]
  bash scripts/platform.sh status
  bash scripts/platform.sh logs [backend|worker|frontend] [--follow]
  bash scripts/platform.sh db-check
  bash scripts/platform.sh start-db
  bash scripts/platform.sh stop-db

Modes:
  dev     Uvicorn reload and Vite development server (default)
  server  Uvicorn without reload and a built Vite preview server
  static  Uvicorn without reload; frontend served directly by Nginx
EOF
}

info() {
  printf '[platform] %s\n' "$*"
}

fail() {
  printf '[platform] ERROR: %s\n' "$*" >&2
  exit 1
}

require_command() {
  command -v "$1" >/dev/null 2>&1 || fail "Required command not found: $1"
}

configure_user_tools() {
  local npm_path
  if ! command -v uv >/dev/null 2>&1 && [[ -x "$HOME/.local/bin/uv" ]]; then
    export PATH="$HOME/.local/bin:$PATH"
  fi

  npm_path="$(command -v npm 2>/dev/null || true)"
  if [[ -z "$npm_path" || "$npm_path" == /mnt/* ]]; then
    export NVM_DIR="${NVM_DIR:-$HOME/.nvm}"
    if [[ -s "$NVM_DIR/nvm.sh" ]]; then
      # shellcheck disable=SC1090
      source "$NVM_DIR/nvm.sh"
      nvm use default >/dev/null
    fi
  fi
}

load_platform_env() {
  if [[ ! -f "$PLATFORM_ENV_FILE" ]]; then
    fail "Missing $PLATFORM_ENV_FILE. Copy .env.platform.example and set the database password first."
  fi

  set -a
  # This is an administrator-owned, shell-compatible environment file.
  # shellcheck disable=SC1090
  source "$PLATFORM_ENV_FILE"
  set +a

  : "${POSTGRES_USER:=ascend_platform}"
  : "${POSTGRES_PASSWORD:?POSTGRES_PASSWORD is required in $PLATFORM_ENV_FILE}"
  : "${POSTGRES_DB:=ascend_platform}"
  : "${POSTGRES_PORT:=15432}"
  : "${BACKEND_HOST:=0.0.0.0}"
  : "${BACKEND_PORT:=8000}"
  : "${FRONTEND_HOST:=0.0.0.0}"
  : "${FRONTEND_PORT:=5173}"
  : "${PLATFORM_MODE:=dev}"
  : "${FRONTEND_DEPLOY_DIR:=/var/www/mskpp-aibench}"
  : "${NGINX_HEALTH_URL:=http://127.0.0.1/elb-health}"
  : "${PLATFORM_PUBLIC_URL:=http://127.0.0.1}"
  export POSTGRES_USER POSTGRES_PASSWORD POSTGRES_DB POSTGRES_PORT
  export BACKEND_HOST BACKEND_PORT FRONTEND_HOST FRONTEND_PORT PLATFORM_MODE
  export FRONTEND_DEPLOY_DIR NGINX_HEALTH_URL PLATFORM_PUBLIC_URL
}

compose() {
  docker compose \
    --project-directory "$PROJECT_ROOT" \
    --env-file "$PLATFORM_ENV_FILE" \
    -f "$PROJECT_ROOT/compose.yaml" \
    "$@"
}

container_exists() {
  docker inspect "$DB_CONTAINER" >/dev/null 2>&1
}

database_mount_name() {
  docker inspect \
    --format '{{range .Mounts}}{{if eq .Destination "/var/lib/postgresql/data"}}{{.Name}}{{end}}{{end}}' \
    "$DB_CONTAINER" 2>/dev/null
}

check_database_mount() {
  local mount_name

  if ! container_exists; then
    info "Database container does not exist; Compose will create it with named volume $DB_VOLUME."
    return 0
  fi

  mount_name="$(database_mount_name)"
  if [[ "$mount_name" != "$DB_VOLUME" ]]; then
    cat >&2 <<EOF
[platform] ERROR: $DB_CONTAINER is mounted to '${mount_name:-unknown}', not '$DB_VOLUME'.
[platform] Refusing to start because recreating the container could hide historical tasks.
[platform] Run 'bash scripts/migrate-postgres-volume.sh', then retry.
EOF
    return 1
  fi

  info "Database mount verified: $DB_VOLUME"
}

wait_for_database() {
  local attempt
  for attempt in {1..60}; do
    if docker exec "$DB_CONTAINER" \
      pg_isready -U "$POSTGRES_USER" -d "$POSTGRES_DB" >/dev/null 2>&1; then
      info "PostgreSQL is accepting connections."
      return 0
    fi
    sleep 1
  done
  docker logs --tail 40 "$DB_CONTAINER" >&2 || true
  fail "PostgreSQL did not become ready within 60 seconds."
}

start_database() {
  require_command docker
  docker info >/dev/null 2>&1 || fail "Docker daemon is not available."
  docker compose version >/dev/null 2>&1 || fail "Docker Compose plugin is not available."
  check_database_mount

  if container_exists; then
    docker start "$DB_CONTAINER" >/dev/null
  else
    if ! docker volume inspect "$DB_VOLUME" >/dev/null 2>&1; then
      info "Creating external named volume $DB_VOLUME..."
      docker volume create "$DB_VOLUME" >/dev/null
    fi
    compose up -d postgres
  fi
  wait_for_database
}

stop_database() {
  if container_exists; then
    info "Stopping PostgreSQL container..."
    docker stop --time 20 "$DB_CONTAINER" >/dev/null
    info "PostgreSQL stopped; its volume was not removed."
  else
    info "PostgreSQL container does not exist."
  fi
}

pid_file() {
  printf '%s/%s.pid\n' "$PID_DIR" "$1"
}

process_marker() {
  case "$1" in
    backend) printf 'uvicorn app.main:app' ;;
    worker) printf 'worker/simulation_worker.py' ;;
    frontend) printf 'npm run' ;;
    *) return 1 ;;
  esac
}

managed_pid() {
  local name="$1"
  local file pid marker cmdline
  file="$(pid_file "$name")"
  [[ -f "$file" ]] || return 1
  read -r pid < "$file"
  [[ "$pid" =~ ^[0-9]+$ ]] || return 1
  kill -0 "$pid" >/dev/null 2>&1 || return 1
  marker="$(process_marker "$name")"
  cmdline="$(tr '\0' ' ' < "/proc/$pid/cmdline" 2>/dev/null || true)"
  [[ "$cmdline" == *"$marker"* ]] || return 1
  printf '%s\n' "$pid"
}

remove_stale_pid() {
  local name="$1"
  if ! managed_pid "$name" >/dev/null 2>&1; then
    rm -f "$(pid_file "$name")"
  fi
}

port_in_use() {
  local port="$1"
  if command -v ss >/dev/null 2>&1; then
    ss -ltnH "sport = :$port" 2>/dev/null | grep -q .
    return
  fi
  (echo >/dev/tcp/127.0.0.1/"$port") >/dev/null 2>&1
}

start_process() {
  local name="$1"
  local working_dir="$2"
  shift 2
  local existing_pid log_path pid

  remove_stale_pid "$name"
  if existing_pid="$(managed_pid "$name" 2>/dev/null)"; then
    info "$name is already running (PID $existing_pid)."
    return 0
  fi

  log_path="$LOG_DIR/$name.log"
  (
    cd "$working_dir"
    nohup setsid "$@" >>"$log_path" 2>&1 </dev/null &
    printf '%s\n' "$!" >"$(pid_file "$name").tmp"
  )
  mv "$(pid_file "$name").tmp" "$(pid_file "$name")"
  read -r pid < "$(pid_file "$name")"
  sleep 1

  if ! kill -0 "$pid" >/dev/null 2>&1; then
    tail -n 30 "$log_path" >&2 || true
    rm -f "$(pid_file "$name")"
    fail "$name failed to start."
  fi
  info "Started $name (PID $pid, log $log_path)."
}

stop_process() {
  local name="$1"
  local pid attempt
  if ! pid="$(managed_pid "$name" 2>/dev/null)"; then
    rm -f "$(pid_file "$name")"
    info "$name is not running."
    return 0
  fi

  info "Stopping $name (PID $pid)..."
  kill -INT -- "-$pid" >/dev/null 2>&1 || kill -INT "$pid" >/dev/null 2>&1 || true
  for attempt in {1..50}; do
    kill -0 "$pid" >/dev/null 2>&1 || break
    sleep 0.1
  done
  if kill -0 "$pid" >/dev/null 2>&1; then
    kill -TERM -- "-$pid" >/dev/null 2>&1 || kill -TERM "$pid" >/dev/null 2>&1 || true
    for attempt in {1..50}; do
      kill -0 "$pid" >/dev/null 2>&1 || break
      sleep 0.1
    done
  fi
  if kill -0 "$pid" >/dev/null 2>&1; then
    kill -KILL -- "-$pid" >/dev/null 2>&1 || kill -KILL "$pid" >/dev/null 2>&1 || true
  fi
  rm -f "$(pid_file "$name")"
  info "Stopped $name."
}

wait_for_http() {
  local name="$1"
  local url="$2"
  local attempt
  for attempt in {1..60}; do
    if curl --fail --silent --show-error "$url" >/dev/null 2>&1; then
      info "$name health check passed: $url"
      return 0
    fi
    sleep 1
  done
  tail -n 40 "$LOG_DIR/$name.log" >&2 || true
  return 1
}

require_backend_environment() {
  [[ -x "$BACKEND_PYTHON" ]] || fail "Missing $BACKEND_PYTHON. Run 'bash scripts/platform.sh setup'."
  [[ -x "$BACKEND_UVICORN" ]] || fail "Missing $BACKEND_UVICORN. Run 'bash scripts/platform.sh setup'."
  [[ -x "$BACKEND_ALEMBIC" ]] || fail "Missing $BACKEND_ALEMBIC. Run 'bash scripts/platform.sh setup'."
}

frontend_dependencies_ready() {
  [[ -x "$FRONTEND_DIR/node_modules/.bin/vite" ]] && \
    (cd "$FRONTEND_DIR" && ./node_modules/.bin/vite --version >/dev/null 2>&1)
}

require_frontend_dependencies() {
  frontend_dependencies_ready || \
    fail "Frontend dependencies are missing. Run 'bash scripts/platform.sh setup'."
}

require_applications_stopped() {
  local name
  for name in backend worker frontend; do
    if managed_pid "$name" >/dev/null 2>&1; then
      fail "Application processes must be stopped before setup/update. Run 'bash scripts/platform.sh stop-apps'."
    fi
  done
  if command -v pgrep >/dev/null 2>&1 && \
     pgrep -f 'uvicorn app.main:app|worker/simulation_worker.py' >/dev/null 2>&1; then
    fail "An unmanaged Backend or Worker process is running. Stop it before setup/update."
  fi
  if port_in_use "$FRONTEND_PORT"; then
    fail "Frontend port $FRONTEND_PORT is in use. Stop the frontend before setup/update."
  fi
}

sync_dependencies() {
  local current_frontend_lock recorded_frontend_lock
  configure_user_tools
  require_command uv
  require_command npm
  require_command sha256sum

  info "Synchronizing backend dependencies..."
  (cd "$BACKEND_DIR" && UV_PROJECT_ENVIRONMENT="$BACKEND_VENV" uv sync --frozen)

  current_frontend_lock="$(sha256sum "$FRONTEND_DIR/package-lock.json" | awk '{print $1}')"
  recorded_frontend_lock=""
  if [[ -f "$FRONTEND_LOCK_STAMP" ]]; then
    read -r recorded_frontend_lock < "$FRONTEND_LOCK_STAMP"
  fi

  if ! frontend_dependencies_ready; then
    info "Installing frontend dependencies..."
    (cd "$FRONTEND_DIR" && npm ci)
  elif [[ -n "$recorded_frontend_lock" && "$recorded_frontend_lock" != "$current_frontend_lock" ]]; then
    info "Frontend lockfile changed; reinstalling dependencies..."
    (cd "$FRONTEND_DIR" && npm ci)
  else
    info "Frontend dependencies are already available."
  fi
  printf '%s\n' "$current_frontend_lock" > "$FRONTEND_LOCK_STAMP"
}

run_migrations() {
  require_backend_environment
  info "Applying database migrations..."
  (cd "$BACKEND_DIR" && "$BACKEND_ALEMBIC" upgrade head)
}

build_frontend() {
  require_frontend_dependencies
  info "Building frontend..."
  (cd "$FRONTEND_DIR" && npm run build)
}

setup_platform() {
  load_platform_env
  require_applications_stopped
  sync_dependencies
  info "Setup complete. Run 'bash scripts/platform.sh update' before the first server start."
}

update_platform_files() {
  load_platform_env
  require_applications_stopped
  sync_dependencies
  start_database
  run_migrations
  build_frontend
  info "Update complete. Run 'bash scripts/platform.sh start ${PLATFORM_MODE}'."
}

start_platform() {
  local requested_mode="${1:-}"
  local mode
  local backend_port frontend_port
  local -a backend_command frontend_command

  load_platform_env
  mode="${requested_mode:-$PLATFORM_MODE}"
  [[ "$mode" == dev || "$mode" == server || "$mode" == static ]] || \
    fail "Mode must be 'dev', 'server', or 'static'."
  if [[ -f "$MODE_FILE" ]] && \
     { managed_pid backend >/dev/null 2>&1 || managed_pid frontend >/dev/null 2>&1; }; then
    read -r active_mode < "$MODE_FILE"
    if [[ "$active_mode" != "$mode" ]]; then
      fail "Platform is already running in $active_mode mode. Use 'restart $mode' to change modes."
    fi
  fi
  backend_port="$BACKEND_PORT"
  frontend_port="$FRONTEND_PORT"
  configure_user_tools
  require_command curl
  require_backend_environment
  if [[ "$mode" != static ]]; then
    require_command npm
    require_frontend_dependencies
  fi
  start_database
  run_migrations

  remove_stale_pid backend
  remove_stale_pid frontend
  if [[ "$mode" == static ]] && managed_pid frontend >/dev/null 2>&1; then
    stop_process frontend
  fi
  if ! managed_pid backend >/dev/null 2>&1 && port_in_use "$backend_port"; then
    fail "Backend port $backend_port is already in use by an unmanaged process."
  fi
  if [[ "$mode" != static ]] && \
     ! managed_pid frontend >/dev/null 2>&1 && \
     port_in_use "$frontend_port"; then
    fail "Frontend port $frontend_port is already in use by an unmanaged process."
  fi

  backend_command=(env PYTHONUNBUFFERED=1 "$BACKEND_UVICORN" app.main:app --host "$BACKEND_HOST" --port "$backend_port")
  if [[ "$mode" == dev ]]; then
    backend_command+=(--reload)
    frontend_command=(npm run dev -- --host "$FRONTEND_HOST" --port "$frontend_port" --strictPort)
  elif [[ "$mode" == server ]]; then
    [[ -f "$FRONTEND_DIR/dist/index.html" ]] || \
      fail "Frontend build is missing. Run 'bash scripts/platform.sh update'."
    frontend_command=(npm run preview -- --host "$FRONTEND_HOST" --port "$frontend_port" --strictPort)
  else
    [[ -f "$FRONTEND_DEPLOY_DIR/index.html" ]] || \
      fail "Nginx frontend files are missing from $FRONTEND_DEPLOY_DIR."
  fi

  start_process backend "$BACKEND_DIR" "${backend_command[@]}"
  if ! wait_for_http backend "http://127.0.0.1:$backend_port/health"; then
    stop_process backend
    fail "Backend health check failed."
  fi

  start_process worker "$BACKEND_DIR" \
    env PYTHONPATH="$BACKEND_DIR" PYTHONUNBUFFERED=1 "$BACKEND_PYTHON" worker/simulation_worker.py
  if [[ "$mode" == static ]]; then
    if ! curl --fail --silent --show-error "$NGINX_HEALTH_URL" >/dev/null; then
      stop_process worker
      stop_process backend
      fail "Nginx static frontend health check failed: $NGINX_HEALTH_URL"
    fi
    info "Nginx static frontend health check passed: $NGINX_HEALTH_URL"
  else
    start_process frontend "$FRONTEND_DIR" "${frontend_command[@]}"
    if ! wait_for_http frontend "http://127.0.0.1:$frontend_port"; then
      stop_process frontend
      stop_process worker
      stop_process backend
      fail "Frontend health check failed."
    fi
  fi

  info "Platform started in $mode mode."
  printf '%s\n' "$mode" > "$MODE_FILE"
  if [[ "$mode" == static ]]; then
    info "Frontend: served by Nginx from $FRONTEND_DEPLOY_DIR"
    info "Public URL: $PLATFORM_PUBLIC_URL"
  else
    info "Frontend: http://127.0.0.1:$frontend_port"
  fi
  info "API docs: http://127.0.0.1:$backend_port/docs"
}

stop_platform() {
  load_platform_env
  stop_applications
  stop_database
}

stop_applications() {
  stop_process frontend
  stop_process worker
  stop_process backend
  rm -f "$MODE_FILE"
}

print_process_status() {
  local name="$1"
  local pid
  if pid="$(managed_pid "$name" 2>/dev/null)"; then
    printf '%-10s running (PID %s)\n' "$name" "$pid"
  else
    printf '%-10s stopped\n' "$name"
  fi
}

platform_status() {
  load_platform_env
  if [[ -f "$MODE_FILE" ]]; then
    printf '%-10s %s\n' mode "$(<"$MODE_FILE")"
  else
    printf '%-10s unknown\n' mode
  fi
  print_process_status backend
  print_process_status worker
  print_process_status frontend
  if container_exists; then
    printf '%-10s %s (mount: %s)\n' \
      database \
      "$(docker inspect --format '{{.State.Status}}' "$DB_CONTAINER")" \
      "$(database_mount_name)"
  else
    printf '%-10s missing\n' database
  fi
}

show_logs() {
  local name="${1:-}"
  local follow="${2:-}"
  local -a files=()
  if [[ -n "$name" ]]; then
    process_marker "$name" >/dev/null || fail "Unknown service: $name"
    files+=("$LOG_DIR/$name.log")
  else
    files+=("$LOG_DIR/backend.log" "$LOG_DIR/worker.log" "$LOG_DIR/frontend.log")
  fi
  if [[ "$follow" == --follow || "$follow" == -f ]]; then
    tail -n 80 -f "${files[@]}"
  else
    tail -n 80 "${files[@]}"
  fi
}

command="${1:-}"
case "$command" in
  setup)
    setup_platform
    ;;
  update)
    update_platform_files
    ;;
  start)
    start_platform "${2:-}"
    ;;
  stop)
    stop_platform
    ;;
  stop-apps)
    load_platform_env
    stop_applications
    ;;
  restart)
    stop_platform
    start_platform "${2:-}"
    ;;
  status)
    platform_status
    ;;
  logs)
    show_logs "${2:-}" "${3:-}"
    ;;
  db-check)
    load_platform_env
    check_database_mount
    ;;
  start-db)
    load_platform_env
    start_database
    ;;
  stop-db)
    load_platform_env
    stop_database
    ;;
  help|-h|--help)
    usage
    ;;
  *)
    usage >&2
    exit 2
    ;;
esac
