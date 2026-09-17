#!/bin/sh
set -e

(cd geneco-mcp && alembic upgrade head)

exec uvicorn gateway:app --host 0.0.0.0 --port 8000
