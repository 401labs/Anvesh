#!/usr/bin/env bash
# Brings up the full Anvesh stack (Postgres, automation-server, web-portal)
# via Docker Compose and waits until the web portal is actually reachable.
#
# Usage: ./start.sh          # build (if needed) and start, then follow logs
#        ./start.sh --no-logs  # start and exit without following logs

set -euo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")"

FOLLOW_LOGS=true
if [[ "${1:-}" == "--no-logs" ]]; then
  FOLLOW_LOGS=false
fi

if ! command -v docker >/dev/null 2>&1; then
  echo "Error: docker is not installed. Install Docker Desktop and try again." >&2
  exit 1
fi

if ! docker info >/dev/null 2>&1; then
  echo "Error: Docker daemon is not running. Start Docker Desktop and try again." >&2
  exit 1
fi

echo "==> Starting Anvesh (db, automation-server, web-portal)..."
docker compose up -d --build

wait_for() {
  local name="$1" url="$2" max_attempts=60 attempt=0
  echo -n "==> Waiting for ${name} at ${url} "
  until curl --silent --fail --output /dev/null "${url}"; do
    attempt=$((attempt + 1))
    if [[ "${attempt}" -ge "${max_attempts}" ]]; then
      echo ""
      echo "Error: ${name} did not become ready in time. Check logs with:" >&2
      echo "  docker compose logs ${name}" >&2
      exit 1
    fi
    echo -n "."
    sleep 2
  done
  echo " ready"
}

wait_for "automation-server" "http://localhost:8000/docs"
wait_for "web-portal" "http://localhost:3000"

cat <<'EOF'

==> Anvesh is up.

    Web Portal:   http://localhost:3000
    API:          http://localhost:8000
    Live view:    http://localhost:6080/vnc.html   (while a headed scrape task is running)

    Stop everything with:  docker compose down
    Tail logs with:        docker compose logs -f

EOF

if [[ "${FOLLOW_LOGS}" == true ]]; then
  docker compose logs -f
fi
