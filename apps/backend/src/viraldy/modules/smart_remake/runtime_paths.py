from __future__ import annotations

import os
from pathlib import Path

try:
    from dotenv import load_dotenv
except ImportError:  # pragma: no cover - production uses process-level env vars
    load_dotenv = None

BACKEND_DIR = Path(__file__).resolve().parents[4]
DEFAULT_OUTPUTS_DIR = BACKEND_DIR / "outputs"

if load_dotenv is not None:
    load_dotenv(BACKEND_DIR / ".env", override=False)
    load_dotenv(BACKEND_DIR.parent / ".env", override=False)

OUTPUTS_DIR = Path(os.getenv("SMART_REMAKE_OUTPUT_DIR", str(DEFAULT_OUTPUTS_DIR))).expanduser()
RENDERS_DIR = OUTPUTS_DIR / "renders"

OUTPUTS_DIR.mkdir(parents=True, exist_ok=True)
RENDERS_DIR.mkdir(parents=True, exist_ok=True)
