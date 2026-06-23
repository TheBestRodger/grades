FROM python:3.12-slim AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

COPY backend/requirements.txt /tmp/backend-requirements.txt
RUN python -m pip install --upgrade pip \
    && python -m pip install -r /tmp/backend-requirements.txt

COPY backend ./backend

RUN mkdir -p /app/backend/data/documents

EXPOSE 8000

STOPSIGNAL SIGTERM

HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/api/health/ready', timeout=5).read()" || exit 1

WORKDIR /app/backend

CMD ["python", "-m", "app.run_server"]
