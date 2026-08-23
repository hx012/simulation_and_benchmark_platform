#!/usr/bin/env bash
set -Eeuo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd -- "$SCRIPT_DIR/.." && pwd)"
BACKEND_DIR="$PROJECT_ROOT/backend"
OFFLINE_ROOT="${OFFLINE_ROOT:-$PROJECT_ROOT/deploy/offline/python}"
UV_VERSION="${UV_VERSION:-0.10.9}"
UV_LINUX_BIN="${UV_LINUX_BIN:-}"
PYTHON_IMAGE="${PYTHON_IMAGE:-python:3.10-slim}"

info() {
  printf '[offline-cache] %s\n' "$*"
}

fail() {
  printf '[offline-cache] ERROR: %s\n' "$*" >&2
  exit 1
}

command -v docker >/dev/null 2>&1 || fail "Docker is required."
docker info >/dev/null 2>&1 || fail "Docker daemon is not available."
command -v sha256sum >/dev/null 2>&1 || fail "sha256sum is required."
[[ -f "$BACKEND_DIR/pyproject.toml" ]] || fail "Missing backend/pyproject.toml."
[[ -f "$BACKEND_DIR/uv.lock" ]] || fail "Missing backend/uv.lock."
[[ -n "$UV_LINUX_BIN" ]] || fail "Set UV_LINUX_BIN to the Linux x86_64 uv $UV_VERSION executable."
[[ -x "$UV_LINUX_BIN" ]] || fail "UV_LINUX_BIN is not executable: $UV_LINUX_BIN"

actual_uv_version="$($UV_LINUX_BIN --version | awk '{print $2}')"
[[ "$actual_uv_version" == "$UV_VERSION" ]] || \
  fail "Expected uv $UV_VERSION, found $actual_uv_version at $UV_LINUX_BIN."

mkdir -p "$OFFLINE_ROOT"
build_dir="$(mktemp -d "$OFFLINE_ROOT/build.XXXXXX")"
cache_dir="$build_dir/uv-cache"
lock_sha256="$(sha256sum "$BACKEND_DIR/uv.lock" | awk '{print $1}')"
artifact_name="uv-cache-linux-x86_64-py310-uv${UV_VERSION}-${lock_sha256:0:12}.tar.gz"
artifact_path="$OFFLINE_ROOT/$artifact_name"

cleanup() {
  rm -rf -- "$build_dir"
}
trap cleanup EXIT

mkdir -p "$cache_dir"

info "Using uv $UV_VERSION and $PYTHON_IMAGE."
info "Pulling the Python build image if needed..."
image_ready=0
for attempt in 1 2 3; do
  if docker pull "$PYTHON_IMAGE"; then
    image_ready=1
    break
  fi
  info "Image pull attempt $attempt failed; retrying..."
  sleep 2
done
[[ "$image_ready" == 1 ]] || fail "Unable to pull $PYTHON_IMAGE after 3 attempts."

info "Downloading locked Linux/Python 3.10 dependencies into an isolated cache..."
docker run --rm \
  --mount "type=bind,src=$BACKEND_DIR,dst=/workspace/backend,readonly" \
  --mount "type=bind,src=$cache_dir,dst=/uv-cache" \
  --mount "type=bind,src=$UV_LINUX_BIN,dst=/usr/local/bin/uv,readonly" \
  --workdir /workspace/backend \
  --env UV_CACHE_DIR=/uv-cache \
  --env UV_PROJECT_ENVIRONMENT=/tmp/platform-venv \
  "$PYTHON_IMAGE" \
  uv sync --frozen --no-dev --no-install-project --link-mode copy

info "Verifying that the cache can recreate the environment with networking disabled..."
docker run --rm \
  --network none \
  --mount "type=bind,src=$BACKEND_DIR,dst=/workspace/backend,readonly" \
  --mount "type=bind,src=$cache_dir,dst=/uv-cache" \
  --mount "type=bind,src=$UV_LINUX_BIN,dst=/usr/local/bin/uv,readonly" \
  --workdir /workspace/backend \
  --env UV_CACHE_DIR=/uv-cache \
  --env UV_PROJECT_ENVIRONMENT=/tmp/platform-venv-offline-check \
  "$PYTHON_IMAGE" \
  sh -c 'uv sync --frozen --offline --no-dev --no-install-project --link-mode copy && PYTHONPATH=/workspace/backend /tmp/platform-venv-offline-check/bin/python -c "from app.main import app; print(app.title)"'

printf '%s\n' \
  "uv_version=$UV_VERSION" \
  "python_image=$PYTHON_IMAGE" \
  "target=linux_x86_64_python_3.10" \
  "uv_lock_sha256=$lock_sha256" \
  >"$build_dir/MANIFEST.txt"

info "Creating $artifact_name..."
tar -C "$build_dir" -czf "$artifact_path" MANIFEST.txt uv-cache
(cd "$OFFLINE_ROOT" && sha256sum "$artifact_name" >"$artifact_name.sha256")

info "Offline cache created: $artifact_path"
info "Checksum file: $artifact_path.sha256"
