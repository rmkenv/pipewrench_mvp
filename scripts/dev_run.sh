#!/usr/bin/env bash
set -euo pipefail
export $(grep -v "^#" .env 2>/dev/null | xargs -d "\n" -I {} echo {})
uvicorn app_combined:app --reload --host 0.0.0.0 --port 8000
