#!/bin/bash
set -eo pipefail
DB_NAME="$1"
DB_USER="$1"
DB_PASS="$2"

if [ -z "$DB_NAME" ] || [ -z "$DB_USER" ] || [ -z "$DB_PASS" ]; then
  echo "Usage: $0 <db_name> <db_pass>"
  exit 1
fi

mysql -u "$MARIADB_ADMIN_USER_USERNAME" <<EOF
CREATE DATABASE $DB_NAME;
CREATE USER '$DB_USER'@'%' IDENTIFIED BY '$DB_PASS';
GRANT ALL PRIVILEGES ON $DB_NAME.* TO '$DB_USER'@'%';
FLUSH PRIVILEGES;
EOF