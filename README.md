# Solar IoT Platform — SolarEdge NL

Real-time solar panel telemetry platform for the Netherlands. Ingests IoT data from 30+ solar panels via AWS IoT Core → Kinesis, enriches readings with KNMI weather observations, and surfaces a FastAPI + React dashboard.

---

## Table of Contents

1. [Architecture](#architecture)
2. [Project Structure](#project-structure)
3. [Local Setup](#local-setup)
   - [Option A — Docker Compose (recommended)](#option-a--docker-compose-recommended)
   - [Option B — Mixed (Postgres in Docker, services locally)](#option-b--mixed-postgres-in-docker-services-locally)
4. [Development Workflow](#development-workflow)
   - [Branching strategy](#branching-strategy)
   - [Adding a feature (feat)](#adding-a-feature-feat)
   - [Adding an improvement (imp)](#adding-an-improvement-imp)
   - [Adding a bug fix (fix)](#adding-a-bug-fix-fix)
   - [Commit messages](#commit-messages)
5. [CI / CD Pipeline](#ci--cd-pipeline)
   - [CI — what runs and when](#ci--what-runs-and-when)
   - [CD — AWS deployment](#cd--aws-deployment)
   - [Setting up GitHub secrets](#setting-up-github-secrets)
6. [Manual AWS Deployment](#manual-aws-deployment)
7. [Key Design Decisions](#key-design-decisions)

---

## Architecture

```
Panels (MQTT)
    │
    ▼ AWS IoT Core rule
┌───────────────────────┐
│  Kinesis panels-stream │  ◄──── Lambda: knmi-poller (EventBridge 10 min)
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

Five AWS CDK stacks (TypeScript):

| Stack | Purpose |
|---|---|
| `IoT-NetworkStack` | VPC, subnets, NAT gateway, S3 gateway endpoint |
| `IoT-DataStack` | Kinesis streams, RDS Aurora Serverless v2, S3 archive bucket |
| `IoT-ComputeStack` | 3× Lambda, IoT Core rule, ECS Fargate, ALB |
| `IoT-FrontendStack` | CloudFront distribution, S3 SPA bucket |
| `IoT-ObservabilityStack` | CloudWatch alarms + dashboard, X-Ray group, SNS alerts |

---

## Project Structure

```
.
├── docker-compose.yml       # Local development stack
├── .env.example             # Environment variable template
├── Makefile                 # Developer shortcuts
├── infra/                   # AWS CDK v2 TypeScript (5 stacks)
│   ├── bin/app.ts
│   └── lib/
│       ├── network-stack.ts
│       ├── data-stack.ts
│       ├── compute-stack.ts
│       ├── frontend-stack.ts
│       └── observability-stack.ts
├── services/
│   ├── api/                 # FastAPI (Python 3.11, uv, asyncpg)
│   │   ├── Dockerfile
│   │   ├── app/
│   │   │   ├── main.py
│   │   │   ├── config.py
│   │   │   ├── database.py
│   │   │   ├── models/
│   │   │   ├── routers/
│   │   │   └── services/
│   │   └── alembic/         # DB migrations
│   ├── panel-processor/     # Lambda: Kinesis panels/weather consumer
│   └── knmi-poller/         # Lambda: KNMI Open Data API poller
├── frontend/                # React + Vite + TypeScript + Recharts
│   ├── Dockerfile.dev       # Dev image for Docker Compose
│   └── src/
├── scripts/
│   ├── seed_db.py           # Seed sites + panels
│   ├── simulate_panels.py   # Simulate IoT telemetry → Kinesis
│   └── check_knmi.py        # KNMI API connectivity check
└── .github/
    └── workflows/
        └── ci.yml           # CI (all branches) + CD (main only)
```

---

## Local Setup

### Prerequisites

- [Docker Desktop](https://docs.docker.com/get-docker/) (includes Docker Compose)
- Python ≥ 3.11 + [uv](https://github.com/astral-sh/uv) (for running tests and scripts locally)
- Node.js ≥ 20 + npm (for CDK and frontend, if not using Docker)

### Option A — Docker Compose (recommended)

The quickest way to get the full stack running locally.

```bash
# 1. Copy environment template
cp .env.example .env

# 2. Start all services (Postgres + API + frontend dev server)
make docker-up
# or: docker compose up --build -d

# 3. Apply database migrations
make migrate

# 4. (Optional) Seed demo data
DATABASE_URL=postgresql+asyncpg://solar:solar@localhost:5432/solar \
  python scripts/seed_db.py
```

Services available after startup:

| Service | URL |
|---|---|
| React frontend | http://localhost:5173 |
| FastAPI | http://localhost:8000 |
| API docs (Swagger) | http://localhost:8000/docs |
| PostgreSQL | localhost:5432 (user/pass/db: `solar`) |

Stop everything:

```bash
make docker-down
# or: docker compose down
```

View logs:

```bash
make docker-logs
# or: docker compose logs -f api
```

### Option B — Mixed (Postgres in Docker, services locally)

Preferred when you want **hot-reload** for the API or frontend without rebuilding Docker images.

```bash
# 1. Copy environment template
cp .env.example .env

# 2. Start only Postgres
make docker-up-db
# or: docker compose up postgres -d

# 3. Install all Python + Node deps
make setup

# 4. Apply DB migrations
make migrate

# 5. Start FastAPI with hot-reload
cd services/api
DATABASE_URL=postgresql+asyncpg://solar:solar@localhost:5432/solar \
  uv run uvicorn app.main:app --reload --port 8000

# 6. In a separate terminal, start the frontend dev server
cd frontend
npm run dev
# → http://localhost:5173 (Vite proxies /api/* to http://localhost:8000)
```

---

## Development Workflow

### Branching strategy

All development happens on short-lived branches off `main`. Use the following prefixes:

| Prefix | Use for | Example |
|---|---|---|
| `feat/` | New user-facing feature | `feat/anomaly-dashboard` |
| `imp/` | Improvement to existing functionality | `imp/kinesis-retry-logic` |
| `fix/` | Bug fix | `fix/knmi-station-code-type` |

```
main
 └── feat/anomaly-dashboard      ← feature branch
 └── imp/kinesis-retry-logic     ← improvement branch
 └── fix/knmi-station-code-type  ← fix branch
```

Never commit directly to `main`. Open a pull request and get CI green before merging.

---

### Adding a feature (feat)

```bash
# 1. Create a feature branch from main
git checkout main && git pull origin main
git checkout -b feat/your-feature-name

# 2. Install / sync deps if you added any
cd services/api && uv sync        # Python
cd frontend && npm install         # Node

# 3. Write code + tests
#    - Add or update models in services/api/app/models/
#    - Add or update routers in services/api/app/routers/
#    - Add or update DB migration: cd services/api && uv run alembic revision --autogenerate -m "describe change"

# 4. Make sure quality gates pass
make lint
make typecheck
make test

# 5. Push and open a PR
git push -u origin feat/your-feature-name
# Open PR → main on GitHub
```

**Checklist before opening a PR:**
- [ ] Tests added / updated (`pytest` passes)
- [ ] `mypy --strict` clean
- [ ] Alembic migration created for any schema change
- [ ] README or docstrings updated if behaviour changed

---

### Adding an improvement (imp)

Improvements are refactors, performance work, dependency upgrades, or DX changes that don't add new user-facing features.

```bash
git checkout main && git pull origin main
git checkout -b imp/your-improvement

# Make changes, then:
make lint && make typecheck && make test
git push -u origin imp/your-improvement
```

---

### Adding a bug fix (fix)

```bash
git checkout main && git pull origin main
git checkout -b fix/short-description

# 1. Write a failing test that reproduces the bug first
# 2. Fix the bug
# 3. Confirm the test now passes
make test

git push -u origin fix/short-description
```

---

### Commit messages

Follow [Conventional Commits](https://www.conventionalcommits.org/):

```
<type>(<scope>): <short summary>

[optional body]
```

| Type | When to use |
|---|---|
| `feat` | New feature |
| `imp` | Improvement / refactor (non-breaking) |
| `fix` | Bug fix |
| `chore` | Build, CI, tooling, dependency bumps |
| `docs` | Documentation only |
| `test` | Tests only |

Examples:

```
feat(api): add /sites/{id}/anomalies endpoint
fix(panel-processor): handle missing irradiance field in KNMI payload
imp(infra): increase Lambda memory for panel-processor to 1024 MB
chore(deps): bump aws-cdk-lib to 2.140.0
```

---

## CI / CD Pipeline

Two separate workflow files keep concerns cleanly separated:

| File | Trigger | Purpose |
|---|---|---|
| `.github/workflows/ci.yml` | Every push + PRs | Lint, type-check, test, build |
| `.github/workflows/cd.yml` | CI passes on `main` | Deploy to AWS |

### CI — what runs and when

Runs on every push to `main`, `feat/*`, `imp/*`, `fix/*`, `claude/*`, and on every pull request targeting `main`.

```
┌──────────────────────────────────────────────────────────────────┐
│  ci.yml (all branches + PRs)                                     │
│                                                                  │
│  python (×3)          cdk             frontend                   │
│  ├─ ruff              ├─ tsc          ├─ tsc --noEmit            │
│  ├─ black             └─ cdk synth    └─ vite build              │
│  ├─ isort                                                        │
│  ├─ mypy --strict                                                │
│  └─ pytest                                                       │
└──────────────────────────────────────────────────────────────────┘
```

### CD — AWS deployment

`cd.yml` is triggered by `workflow_run` — it starts only when CI completes **successfully** on `main`, so a broken CI always blocks deployment. It:

1. Configures AWS credentials from GitHub secrets
2. Runs `cdk deploy --all` (builds & pushes the ECS Docker image to ECR, updates all Lambda code, provisions/updates all CloudFormation stacks)
3. Reads stack outputs from `cdk-outputs.json`
4. Builds the React SPA with `VITE_API_URL` pointing to the ALB
5. Syncs `frontend/dist` to the S3 bucket (immutable cache headers on assets, no-cache on `index.html`)
6. Creates a CloudFront invalidation for `/*`

```
push to main
     │
     ▼ ci.yml passes
┌─────────────────────────────────────────────────────────────────┐
│  cd.yml — deploy job                                            │
│                                                                 │
│  configure-aws-credentials                                      │
│       │                                                         │
│       ▼                                                         │
│  cdk deploy --all ──► ECR (API image) + CloudFormation stacks   │
│       │                                                         │
│       ▼                                                         │
│  Read outputs (API URL, S3 bucket, CF distribution)             │
│       │                                                         │
│       ▼                                                         │
│  npm run build (VITE_API_URL=<ALB URL>)                         │
│       │                                                         │
│       ▼                                                         │
│  aws s3 sync → S3 bucket                                        │
│       │                                                         │
│       ▼                                                         │
│  aws cloudfront create-invalidation                             │
└─────────────────────────────────────────────────────────────────┘
```

### Setting up GitHub secrets

Go to **Settings → Secrets and variables → Actions** and add:

| Name | Where to get it | Type |
|---|---|---|
| `AWS_ACCESS_KEY_ID` | IAM → Users → Security credentials | Secret |
| `AWS_SECRET_ACCESS_KEY` | IAM → Users → Security credentials | Secret |

Go to **Settings → Secrets and variables → Actions → Variables** and add:

| Name | Example value | Type |
|---|---|---|
| `AWS_REGION` | `eu-west-1` | Variable |

**Recommended IAM policy**: Attach `AdministratorAccess` to the deploy user for initial setup. Scope it down to required services (CloudFormation, ECR, ECS, Lambda, S3, CloudFront, IAM, Kinesis, RDS, Secrets Manager, IoT, Events) once the platform is stable.

---

## Manual AWS Deployment

Use this for the initial bootstrap or when you need to deploy without CI.

```bash
# 0. Prerequisites: AWS CLI configured, Docker running, Node ≥ 20

# 1. Bootstrap CDK (once per account/region)
cd infra && npx cdk bootstrap

# 2. Store KNMI API key in Secrets Manager before first deploy
aws secretsmanager create-secret \
  --name iot-platform/knmi-api-key \
  --secret-string "YOUR_KNMI_KEY"

# 3. Deploy all stacks (builds Docker image, pushes to ECR, provisions infra)
make deploy
# or: cd infra && npm run build && npx cdk deploy --all

# 4. Seed the database (get the RDS endpoint from the Secrets Manager secret)
DATABASE_URL=postgresql+asyncpg://solar:solar@<RDS_HOST>:5432/solar \
  python scripts/seed_db.py

# 5. Build and upload the frontend
API_URL=$(aws cloudformation describe-stacks \
  --stack-name IoT-ComputeStack \
  --query 'Stacks[0].Outputs[?OutputKey==`ApiUrl`].OutputValue' \
  --output text)

cd frontend
VITE_API_URL="$API_URL" npm run build

BUCKET=$(aws cloudformation describe-stacks \
  --stack-name IoT-FrontendStack \
  --query 'Stacks[0].Outputs[?OutputKey==`SiteBucketName`].OutputValue' \
  --output text)

aws s3 sync dist "s3://$BUCKET" --delete

DIST_ID=$(aws cloudformation describe-stacks \
  --stack-name IoT-FrontendStack \
  --query 'Stacks[0].Outputs[?OutputKey==`DistributionId`].OutputValue' \
  --output text)

aws cloudfront create-invalidation --distribution-id "$DIST_ID" --paths "/*"
```

---

## Key Design Decisions

- **Anomaly threshold**: `ac_power < 60% of expected` (strict `<`; exactly 60% is NOT anomalous). Constant defined in both Lambda (`panel-processor/src/transform.py`) and API (`services/api/app/services/anomaly.py`).
- **KNMI station codes are always strings** (`"344"`, never `344`). Enforced in all Pydantic models, API types, and frontend TypeScript types.
- **Kinesis partition key = panel_id / station_code** — preserves per-entity ordering.
- **S3 archive prefix**: `raw/panels/YYYY/MM/DD/{panel_id}.json` — partitioned for Athena.
- **Aurora Serverless v2 scales to 0.5 ACU minimum** — cost-optimised for dev; raise min in prod.
- **CloudFront OAC** (not legacy OAI) for S3 origin access.
- **DATABASE_URL env var bypasses Secrets Manager** — used in Docker Compose and tests; in AWS the `DB_SECRET_ARN` path is used instead.
