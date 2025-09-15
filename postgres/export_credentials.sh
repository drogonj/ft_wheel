#!/bin/sh
set -e

echo "Exporting PostgreSQL credentials from secrets..."
[ -f /run/secrets/postgres_password ] && export POSTGRES_PASSWORD="$(cat /run/secrets/postgres_password)"
[ -f /run/secrets/postgres_db ] && export POSTGRES_DB="$(cat /run/secrets/postgres_db)"

if [ -z "$POSTGRES_PASSWORD" ]; then
  echo "Error: POSTGRES_PASSWORD is not set. Please provide a valid password."
  exit 1
fi
if [ -z "$POSTGRES_DB" ]; then
  echo "Error: POSTGRES_DB is not set. Please provide a valid database name."
  exit 1
fi
echo "PostgreSQL credentials exported successfully."

exec docker-entrypoint.sh "$@"