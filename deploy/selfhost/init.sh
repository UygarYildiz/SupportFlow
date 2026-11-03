#!/bin/sh
# Create .env with random secrets for a self-hosted SupportFlow (docs/SELF_HOSTING.md).
set -eu
cd "$(dirname "$0")"

if [ -f .env ]; then
  echo ".env already exists; leaving it unchanged (delete it to start over)."
  grep '^SETUP_TOKEN=' .env || true
  exit 0
fi

random() { od -An -N"$1" -tx1 /dev/urandom | tr -d ' \n'; }

POSTGRES_PASSWORD=$(random 24)
JWT_SECRET_KEY=$(random 32)
SETUP_TOKEN=$(random 12)

umask 077
sed -e "s/^POSTGRES_PASSWORD=.*/POSTGRES_PASSWORD=$POSTGRES_PASSWORD/" \
    -e "s/^JWT_SECRET_KEY=.*/JWT_SECRET_KEY=$JWT_SECRET_KEY/" \
    -e "s/^SETUP_TOKEN=.*/SETUP_TOKEN=$SETUP_TOKEN/" \
    .env.example > .env

echo "Created .env with random secrets."
echo
echo "  Setup code: $SETUP_TOKEN"
echo
echo "Next: docker compose up -d --build, then open http://localhost:8080"
