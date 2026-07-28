#!/usr/bin/env sh
set -eu
exec uvicorn viraldy.api.main:app --host 0.0.0.0 --port 8000
