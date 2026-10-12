#!/usr/bin/env sh
# Deploy one commit to this host.
#
#   REGISTRY=ghcr.io/<owner>/<repo> ENV_FILE=/etc/wellbeing/production.env \
#   API_URL=https://api.example.com APP_URL=https://app.example.com \
#   sh infra/deploy.sh <git-commit-sha>
#
# Order matters:
#   1. pull the images for that exact commit
#   2. apply database migrations with the new image, while the old version still serves
#   3. replace the API, worker, scheduler and frontend
#   4. run the smoke tests; on failure, say how to roll back
#
# Migrations must therefore be backwards compatible with the version that is running
# (add first, remove in a later release). See docs/runbook.md "Migrations".
set -eu

SHA="${1:?usage: deploy.sh <git-commit-sha>}"
REGISTRY="${REGISTRY:?set REGISTRY, for example ghcr.io/owner/repo}"
export ENV_FILE="${ENV_FILE:?set ENV_FILE}"
export BACKEND_IMAGE="$REGISTRY-backend:sha-$SHA"
export FRONTEND_IMAGE="$REGISTRY-frontend:sha-$SHA"
STATE_DIR="${STATE_DIR:-/var/lib/wellbeing}"
COMPOSE="docker compose -f $(dirname "$0")/docker-compose.production.yml ${EXTRA_COMPOSE_FILES:-}"

mkdir -p "$STATE_DIR"
PREVIOUS="$(cat "$STATE_DIR/current" 2>/dev/null || echo none)"
echo "Deploying $SHA (currently running: $PREVIOUS)"

echo "1. Pulling images"
$COMPOSE pull --quiet web frontend

echo "2. Applying migrations"
$COMPOSE run --rm migrate

echo "3. Starting the new version"
$COMPOSE up -d --wait --remove-orphans web worker beat frontend

echo "4. Smoke tests"
if sh "$(dirname "$0")/smoke-test.sh"; then
  [ "$PREVIOUS" != "$SHA" ] && echo "$PREVIOUS" > "$STATE_DIR/previous"
  echo "$SHA" > "$STATE_DIR/current"
  echo "Deployed $SHA."
else
  echo "Smoke tests failed. The new version is still running."
  echo "To roll back the code:  sh infra/deploy.sh $PREVIOUS"
  echo "Migrations are not undone automatically; see docs/runbook.md \"Rollback\"."
  exit 1
fi
