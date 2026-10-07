# One image, one URL: the FastAPI backend serves the API at /api/* and the built
# React frontend at /. All data is synthetic and held in memory.

# Stage 1 — build the frontend.
FROM node:22-slim AS frontend
WORKDIR /app/frontend
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci
COPY frontend/ ./
RUN npm run build

# Stage 2 — run the backend with the built frontend alongside it.
FROM python:3.12-slim AS runtime
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PORT=8000
WORKDIR /app
COPY backend/requirements.txt backend/requirements.txt
RUN pip install -r backend/requirements.txt
COPY backend/ backend/
COPY --from=frontend /app/frontend/dist frontend/dist
# Run as an unprivileged user; the app writes nothing to disk.
RUN useradd --create-home --uid 1000 linelens
USER linelens
WORKDIR /app/backend
EXPOSE 8000
# A single worker on purpose: the simulator, incidents and assumptions live in process memory.
CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
