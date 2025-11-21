#!/bin/bash
set -eo pipefail

DB_NAME="$1"
DB_USER="$1"
DB_PASS="$2"

if [ -z "$DB_NAME" ] || [ -z "$DB_USER" ] || [ -z "$DB_PASS" ]; then
  echo "Usage: $0 <db_name> <db_pass> [extension] [extension ...]"
  exit 1
fi

psql -d postgres <<EOF
CREATE DATABASE $DB_NAME;
CREATE USER $DB_USER WITH ENCRYPTED PASSWORD '$DB_PASS';
GRANT ALL PRIVILEGES ON DATABASE $DB_NAME TO $DB_USER;
ALTER DATABASE $DB_NAME OWNER TO $DB_USER;
\c $DB_NAME $PG_ADMIN_USER_USERNAME
ALTER SCHEMA public OWNER TO $DB_USER;
GRANT ALL ON SCHEMA public TO $DB_USER;
EOF

for ext in "${@:3}"
do
  echo "Creating extension $ext in database $DB_NAME"
  psql -U "$PG_ADMIN_USER_USERNAME" -d "$DB_NAME" -c "CREATE EXTENSION IF NOT EXISTS $ext CASCADE;"
done

