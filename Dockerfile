FROM node:22-bookworm-slim AS frontend-build

WORKDIR /app/frontend

COPY frontend/package*.json ./
RUN npm ci --no-audit --no-fund

COPY frontend/ ./
RUN npm run build


FROM python:3.12-slim AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

COPY backend/requirements.txt /tmp/backend-requirements.txt
RUN python -m pip install --upgrade pip \
    && python -m pip install -r /tmp/backend-requirements.txt

COPY backend ./backend
COPY --from=frontend-build /app/frontend/dist ./frontend/dist
COPY ["Изначальные документы_история", "./Изначальные документы_история"]
COPY Гре*ды ./Грейды

RUN mkdir -p /app/backend/data/documents

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/api/health', timeout=5).read()" || exit 1

CMD ["python", "-m", "uvicorn", "app.main:app", "--app-dir", "backend", "--host", "0.0.0.0", "--port", "8000", "--workers", "1"]
