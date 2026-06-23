#!/usr/bin/env bash
set -euo pipefail

SERVICE="${SERVICE:-app}"
POSTGRES_SERVICE="${POSTGRES_SERVICE:-postgres}"
BACKUP_ROOT="${1:-../grades_mgtu_backups}"
STAMP="$(date +%Y%m%d-%H%M%S)"
BACKUP_DIR="${BACKUP_ROOT%/}/${STAMP}"
DOCUMENTS_DIR="/app/backend/data/documents"

mkdir -p "${BACKUP_DIR}"

docker compose exec -T "${POSTGRES_SERVICE}" sh -c \
    'pg_dump -U "$POSTGRES_USER" "$POSTGRES_DB"' \
    > "${BACKUP_DIR}/postgres.sql"

if docker compose exec -T "${SERVICE}" test -d "${DOCUMENTS_DIR}"; then
    docker compose cp "${SERVICE}:${DOCUMENTS_DIR}" "${BACKUP_DIR}/documents"
fi

echo "PostgreSQL backup saved to ${BACKUP_DIR}"
