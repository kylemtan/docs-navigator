#!/bin/bash
set -e

# FastAPI on internal port — not exposed to the internet directly
uvicorn app.main:app --host 127.0.0.1 --port 8000 &

# Next.js handles the public-facing port Render injects
# exec makes it PID 1 so signals (SIGTERM) shut the container cleanly
cd /app/frontend
exec node_modules/.bin/next start -p "${PORT:-3000}"
