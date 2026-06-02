#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
MYSQL_BIN="${MYSQL_BIN:-mysql}"
MYSQL_HOST="${MYSQL_HOST:-localhost}"
MYSQL_USER="${MYSQL_USER:-root}"
MYSQL_DATABASE="${MYSQL_DATABASE:-spotify_explorer}"

if ! command -v "$MYSQL_BIN" >/dev/null 2>&1; then
  if [ -x /usr/local/mysql/bin/mysql ]; then
    MYSQL_BIN="/usr/local/mysql/bin/mysql"
  else
    echo "mysql was not found. Set MYSQL_BIN=/path/to/mysql and rerun." >&2
    exit 1
  fi
fi

MYSQL_ARGS=(--local-infile=1 -h "$MYSQL_HOST" -u "$MYSQL_USER")

if [ -n "${MYSQL_PORT:-}" ]; then
  MYSQL_ARGS+=(--port "$MYSQL_PORT")
fi

if [ -n "${MYSQL_SOCKET:-}" ]; then
  MYSQL_ARGS+=(--socket "$MYSQL_SOCKET")
fi

if [ -n "${MYSQL_PASSWORD:-}" ]; then
  export MYSQL_PWD="$MYSQL_PASSWORD"
fi

echo "Creating schema in $MYSQL_DATABASE..."
"$MYSQL_BIN" "${MYSQL_ARGS[@]}" < "$ROOT_DIR/sql/01_schema.sql"

echo "Enabling LOAD DATA LOCAL INFILE on the MySQL server..."
if ! "$MYSQL_BIN" "${MYSQL_ARGS[@]}" -e "SET GLOBAL local_infile = 1;"; then
  echo "Could not enable local_infile automatically. Run this manually with a MySQL admin user:" >&2
  echo "$MYSQL_BIN -u root -p -e \"SET GLOBAL local_infile = 1;\"" >&2
  exit 1
fi

load_sql="$(mktemp "${TMPDIR:-/tmp}/spotify_load.XXXXXX.sql")"
trap 'rm -f "$load_sql"' EXIT

python3 - "$ROOT_DIR/sql/02_load_spotify_3nf.sql" "$load_sql" "$ROOT_DIR/data/dataset.csv" <<'PY'
from pathlib import Path
import sys

source = Path(sys.argv[1])
dest = Path(sys.argv[2])
dataset = Path(sys.argv[3]).resolve()

sql = source.read_text()
sql = sql.replace("/absolute/path/to/dataset.csv", str(dataset).replace("\\", "\\\\"))
dest.write_text(sql)
PY

echo "Loading data/dataset.csv into $MYSQL_DATABASE..."
"$MYSQL_BIN" "${MYSQL_ARGS[@]}" --database "$MYSQL_DATABASE" < "$load_sql"

echo "Adding indexes and constraints..."
"$MYSQL_BIN" "${MYSQL_ARGS[@]}" --database "$MYSQL_DATABASE" < "$ROOT_DIR/sql/03_indexes_constraints.sql"

echo "Creating spotify_api database user if possible..."
if "$MYSQL_BIN" "${MYSQL_ARGS[@]}" < "$ROOT_DIR/sql/04_api_user.sql"; then
  echo "spotify_api user is ready."
else
  echo "Could not create spotify_api user. Rerun with a MySQL admin account, or set backend/config.json to a user that can access $MYSQL_DATABASE." >&2
fi

if [ ! -f "$ROOT_DIR/backend/config.json" ]; then
  cp "$ROOT_DIR/backend/config.example.json" "$ROOT_DIR/backend/config.json"
  echo "Created backend/config.json from backend/config.example.json."
fi

echo "Database setup complete."
