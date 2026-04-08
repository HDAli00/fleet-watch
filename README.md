# Solar IoT Platform — SolarEdge NL

Real-time solar panel telemetry platform for the Netherlands. Ingests IoT data from 30+ solar panels via AWS IoT Core → Kinesis, enriches readings with KNMI weather observations, and surfaces a FastAPI + React dashboard.

## Architecture

```
Panels (MQTT)
    │
    ▼ AWS IoT Core rule
┌───────────────────────┐
│  Kinesis panels-stream │  ◄──── Lambda: knmi-poller (EventBridge 10min)
└───────────┬───────────┘         │
            │                     ▼
            │             Kinesis weather-stream
            ▼                     │
  Lambda: panel-processor ◄───────┘
  (anomaly detection, DB write, S3 archive)
            │
            ▼
  RDS Aurora PostgreSQL (serverless v2)
            │
            ▼
  ECS Fargate: FastAPI  ──► ALB ──► CloudFront ──► React SPA
```

## Project Structure

```
.
├── infra/               # AWS CDK v2 TypeScript (5 stacks)
│   ├── lib/
│   │   ├── network-stack.ts
│   │   ├── data-stack.ts
│   │   ├── compute-stack.ts
│   │   ├── frontend-stack.ts
│   │   └── observability-stack.ts
│   └── bin/app.ts
├── services/
│   ├── api/             # FastAPI (Python 3.11, uv, asyncpg)
│   ├── panel-processor/ # Lambda: Kinesis panels/weather consumer
│   └── knmi-poller/     # Lambda: KNMI Open Data API poller
├── frontend/            # React + Vite + TypeScript + Recharts
├── scripts/
│   ├── seed_db.py       # Seed sites + panels
│   ├── simulate_panels.py  # Local IoT simulation → Kinesis
│   └── check_knmi.py    # KNMI API connectivity check
└── Makefile
```

## Quick Start

### Prerequisites

- Python ≥ 3.11, [uv](https://github.com/astral-sh/uv)
- Node.js ≥ 20, npm
- AWS CLI configured with appropriate credentials
- Docker (for ECS image build + testcontainers)

### Setup

```bash
make setup          # Install all deps + pre-commit hooks
make lint           # Ruff + Black + isort across all services
make typecheck      # mypy --strict + tsc
make test           # pytest (unit + integration) across all services
make synth          # CDK synth (dry-run)
```

### Deploy

```bash
# Bootstrap CDK (once per account/region)
cd infra && npx cdk bootstrap

# Store KNMI API key in Secrets Manager before deploy
aws secretsmanager create-secret \
  --name iot-platform/knmi-api-key \
  --secret-string "YOUR_KNMI_KEY"

# Deploy all stacks
make deploy
```

### Seed & Simulate

```bash
DATABASE_URL=postgresql+asyncpg://user:pass@host/solar \
  python scripts/seed_db.py

# Simulate 5 panels with 5% anomaly injection every 10s
python scripts/simulate_panels.py \
  --site-id site-NL-001 \
  --panel-count 5 \
  --anomaly-rate 0.05 \
  --interval 10

# Verify KNMI API
KNMI_API_KEY=xxx python scripts/check_knmi.py
```

## Key Design Decisions

- **Anomaly threshold**: `ac_power < 60% of expected` (strict `<`; exactly 60% is NOT anomalous). Constant defined in both Lambda (`panel-processor/src/transform.py`) and API (`services/api/app/services/anomaly.py`).
- **KNMI station codes are always strings** (`"344"`, never `344`). Enforced in all Pydantic models, API types, and frontend TypeScript types.
- **Kinesis partition key = panel_id / station_code** — preserves per-entity ordering.
- **S3 archive prefix**: `raw/panels/YYYY/MM/DD/{panel_id}.json` — partitioned for Athena.
- **Aurora Serverless v2 scales to 0.5 ACU minimum** — cost-optimised for dev; raise min in prod.
- **CloudFront OAC** (not legacy OAI) for S3 origin access.

## CI

GitHub Actions runs on push to `main` and `claude/*`:
- Python: ruff, black, isort, mypy --strict, pytest (per service)
- CDK: tsc + cdk synth