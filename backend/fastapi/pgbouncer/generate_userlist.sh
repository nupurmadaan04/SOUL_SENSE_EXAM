#!/bin/bash
# Script to generate PgBouncer userlist.txt with MD5 hashed passwords
# This script should be run during container startup

set -e

USERLIST_FILE="/etc/pgbouncer/userlist.txt"
DB_USER="${DB_USER:-postgres}"
DB_PASSWORD="${DB_PASSWORD:-password}"

# Generate MD5 hash for PgBouncer authentication
# PgBouncer expects: md5$(md5(password + username) + salt)
# But for simplicity, we'll use a basic MD5 hash
PASSWORD_MD5=$(echo -n "${DB_PASSWORD}${DB_USER}" | md5sum | cut -d' ' -f1)

# Create userlist.txt
cat > "$USERLIST_FILE" << EOF
# PgBouncer user authentication
# Generated at container startup
"${DB_USER}" "md5${PASSWORD_MD5}"
EOF

echo "Generated PgBouncer userlist.txt for user: $DB_USER"
chmod 600 "$USERLIST_FILE"