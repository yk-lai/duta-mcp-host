FROM python:3.12-slim

WORKDIR /app

# Install the shared infrastructure package first so sub-projects can resolve it.
COPY shared/ ./shared/
RUN pip install --no-cache-dir -e ./shared

# Install sub-projects (installs their deps) + gateway deps
COPY geneco-mcp/ ./geneco-mcp/
RUN pip install --no-cache-dir -e ./geneco-mcp \
    "fastapi>=0.115.0" \
    "uvicorn[standard]>=0.34.0"

# Copy gateway
COPY gateway.py ./
COPY docker-entrypoint.sh ./
RUN chmod +x docker-entrypoint.sh

# Non-root user
RUN groupadd --gid 1000 appuser && \
    useradd --uid 1000 --gid 1000 --no-create-home appuser && \
    chown -R appuser:appuser /app
USER appuser

EXPOSE 8000

# Runs geneco-mcp's `alembic upgrade head` before starting uvicorn — this
# service now owns its own Postgres-backed credential store.
CMD ["./docker-entrypoint.sh"]
