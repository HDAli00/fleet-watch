#!/usr/bin/env bash
set -euo pipefail

BASE=${BASE:-http://localhost:8080}
fail() { echo "SMOKE FAIL: $*" >&2; exit 1; }

echo "==> /api/health"
health=$(curl -fsS "$BASE/api/health") || fail "health endpoint did not respond"
echo "$health" | grep -q '"db"' || fail "health response missing db field: $health"
echo "$health" | grep -q '"redis"' || fail "health response missing redis field: $health"

echo "==> SPA shell"
curl -fsS "$BASE/" | grep -q 'id="root"' || fail "SPA shell missing #root"

echo "==> /api/stream/fleet (5s)"
sse=$(curl -N --max-time 5 -fsS "$BASE/api/stream/fleet" || true)
count=$(echo "$sse" | grep -c '^data:' || true)
[[ "$count" -ge 3 ]] || fail "expected >=3 SSE messages, got $count"

echo "==> POST /api/telemetry"
sample='{"vehicle_id":"v-test-0001","ts":"2026-04-28T00:00:00Z","rpm":2200,"speed_kph":80,"coolant_c":92.0,"oil_psi":42.0,"battery_v":13.8,"throttle_pct":35.0,"fuel_pct":62.0,"lat":52.37,"lon":4.9,"heading_deg":120.0}'
curl -fsS -X POST "$BASE/api/telemetry" -H 'content-type: application/json' -d "$sample" >/dev/null \
  || fail "POST /api/telemetry failed"

echo "==> /api/vehicles"
vehicles=$(curl -fsS "$BASE/api/vehicles?limit=5") || fail "GET /api/vehicles failed"
echo "$vehicles" | grep -q '"vehicle_id"' || fail "no vehicle_id in /api/vehicles response"

echo "SMOKE OK"
