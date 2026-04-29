# Fleet Telemetry — `/app`

Live connected-vehicle fleet console: ~500 simulated cars stream 1 reading/sec each through FastAPI + Postgres + Redis (pub/sub + leader-locked generator) and render on a live Leaflet map. Click any vehicle to drill into per-car gauges + 60-min history charts + recent events.

## One-shot local run

From the **repo root**:

```sh
make verify    # lint + types + tests + build + up + migrate + smoke + down
```

Or piecemeal:

```sh
make up        # build + bring stack up at http://localhost:8080
make migrate   # run alembic inside the api container
make smoke     # curl health, SSE, and POST a sample reading
make logs      # tail compose logs
make down      # tear down + prune volumes
```

## Layout

```
app/
├── api/                 FastAPI backend (Python 3.11, uv-managed)
│   ├── app/             config, db, redis_bus, generator, alerts, routes/
│   ├── alembic/         migrations
│   └── tests/           pytest unit tests
├── web/                 React + Vite + TS dashboard
│   └── src/             pages/, components/, hooks/, api/
├── docker-compose.yml   postgres + redis + 2× api + nginx-served web
└── .env.example         all env vars compose reads
```

Dockerfiles live at `/docker/`; the compose file references them via `dockerfile: docker/*.Dockerfile`.

## Stack at a glance

- **API** (FastAPI, asyncpg, redis-py async, sse-starlette) runs as 2 replicas behind nginx.
- A **leader lock** in Redis (`SET NX EX` + Lua-guarded refresh) ensures only one replica drives the synthetic generator.
- **Telemetry writes** are buffered per replica and flushed every `BATCH_FLUSH_MS` (default 500 ms) via `executemany`.
- **SSE** (`/api/stream/fleet`, `/api/stream/vehicles/{id}`) fan out via Redis pub/sub channels (`fleet.positions`, `fleet.events`) so any replica can serve any client.
- **Web** is built into a static bundle and served by `nginx:alpine`, which also reverse-proxies `/api/*` to the api service (round-robin across replicas, SSE-friendly: `proxy_buffering off`, `chunked_transfer_encoding on`).

## API endpoints

- `GET  /health` — `{db, redis, leader, instance}`
- `POST /telemetry` — ingest one reading (open, no auth)
- `GET  /vehicles[?limit=]` — fleet summary with last-known position
- `GET  /vehicles/{id}` — single vehicle summary
- `GET  /vehicles/{id}/history?window_minutes=60` — last N minutes of telemetry
- `GET  /events[?limit=&severity=]` — recent alerts/events
- `GET  /stream/fleet` — SSE: snapshot, then live `kpis` / `positions` / `event`
- `GET  /stream/vehicles/{id}` — SSE: per-vehicle `position` / `event`

## Tuning the demo

All knobs are env vars (see `.env.example`):

- `FLEET_SIZE` (default 500) — how many simulated cars to seed
- `GEN_RATE_HZ` (default 1.0) — readings per car per second
- `GEN_ENABLED` (default true) — turn the generator off for pure ingest mode
- `BATCH_FLUSH_MS`, `BATCH_MAX_ROWS` — Postgres write batching
- `LEADER_LOCK_TTL_S`, `LEADER_REFRESH_S` — generator leader election cadence
