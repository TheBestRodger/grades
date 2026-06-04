#!/usr/bin/env bash
set -euo pipefail

SERVICE="${SERVICE:-app}"
BACKUP_ROOT="${1:-../grades_mgtu_backups}"
STAMP="$(date +%Y%m%d-%H%M%S)"
BACKUP_DIR="${BACKUP_ROOT%/}/${STAMP}"
CONTAINER_DB="/app/backend/data/demo.sqlite"
CONTAINER_DB_BACKUP="/tmp/demo-${STAMP}.sqlite"
DOCUMENTS_DIR="/app/backend/data/documents"

if ! docker compose exec -T "${SERVICE}" test -f "${CONTAINER_DB}"; then
    echo "SQLite database not found in running service '${SERVICE}': ${CONTAINER_DB}" >&2
    exit 1
fi

mkdir -p "${BACKUP_DIR}"

docker compose exec -T "${SERVICE}" python - "${CONTAINER_DB}" "${CONTAINER_DB_BACKUP}" <<'PY'
import sqlite3
import sys
from pathlib import Path

source_path = Path(sys.argv[1])
backup_path = Path(sys.argv[2])

if not source_path.exists():
    raise SystemExit(f"SQLite database not found: {source_path}")

source = sqlite3.connect(source_path)
target = sqlite3.connect(backup_path)
try:
    source.backup(target)
finally:
    target.close()
    source.close()
PY

docker compose cp "${SERVICE}:${CONTAINER_DB_BACKUP}" "${BACKUP_DIR}/demo.sqlite"
docker compose exec -T "${SERVICE}" rm -f "${CONTAINER_DB_BACKUP}"

if docker compose exec -T "${SERVICE}" test -d "${DOCUMENTS_DIR}"; then
    docker compose cp "${SERVICE}:${DOCUMENTS_DIR}" "${BACKUP_DIR}/documents"
fi

echo "Backup saved to ${BACKUP_DIR}"
