from __future__ import annotations

import os

# Tests run without a live DB / redis; force minimal settings.
os.environ.setdefault("DATABASE_URL", "postgresql://fleet:fleet@localhost:5432/fleet")
os.environ.setdefault("REDIS_URL", "redis://localhost:6379/0")
