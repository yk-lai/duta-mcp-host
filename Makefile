.PHONY: install run docker-up docker-down

install:
	python3 -m venv .venv
	.venv/bin/pip install --upgrade pip
	.venv/bin/pip install -e ./shared
	.venv/bin/pip install -e ./geneco-mcp "fastapi>=0.115.0" "uvicorn[standard]>=0.34.0"

run:
	.venv/bin/uvicorn gateway:app --host 0.0.0.0 --port 8000 --reload

docker-up:
	docker compose up --build -d

docker-down:
	docker compose down
