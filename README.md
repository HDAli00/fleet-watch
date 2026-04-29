# Fleet Telemetry

Live connected-vehicle fleet telemetry console. ~500 simulated cars stream 1 reading/sec each through FastAPI + Postgres + Redis, rendered as a live Leaflet map with drill-down per vehicle.

```
make help        # list all targets
make verify      # full local end-to-end (lint + types + tests + build + up + smoke + down)
make up          # bring the stack up at http://localhost:8080
make down        # tear it down
```

App lives in [`app/`](./app). Dockerfiles in [`docker/`](./docker).
