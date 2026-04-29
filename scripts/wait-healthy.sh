#!/usr/bin/env bash
set -euo pipefail
COMPOSE=(docker compose -f app/docker-compose.yml --project-directory app)
TIMEOUT=${TIMEOUT:-120}
deadline=$((SECONDS + TIMEOUT))

while (( SECONDS < deadline )); do
  ids=$("${COMPOSE[@]}" ps -q)
  if [[ -z "$ids" ]]; then sleep 1; continue; fi

  unhealthy=0
  for cid in $ids; do
    state=$(docker inspect --format='{{.State.Health.Status}}{{.State.Status}}' "$cid" 2>/dev/null || echo "")
    case "$state" in
      *healthy*) ;;
      *running*)
        # No healthcheck defined -> treat 'running' as healthy
        ;;
      *)
        unhealthy=1
        ;;
    esac
  done

  if (( unhealthy == 0 )); then
    echo "all services healthy"
    exit 0
  fi
  sleep 2
done

echo "timeout waiting for services to be healthy" >&2
"${COMPOSE[@]}" ps
exit 1
