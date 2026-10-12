#!/usr/bin/env sh
# Smoke tests for a deployed environment. Read-only: creates nothing, signs in nowhere.
#
#   API_URL=https://api.example.com APP_URL=https://app.example.com sh infra/smoke-test.sh
#
# Exits non-zero on the first failure, which stops a deploy.
set -eu

API_URL="${API_URL:?set API_URL}"
APP_URL="${APP_URL:?set APP_URL}"
# For environments reached over plain HTTP behind a TLS-terminating proxy (rehearsal).
PROTO_HEADER="${FORWARDED_PROTO:+X-Forwarded-Proto: $FORWARDED_PROTO}"
HOST_HEADER="${API_HOST:+Host: $API_HOST}"

failures=0
check() {
  description="$1"; expected="$2"; shift 2
  actual="$(curl -sS -o /dev/null -m 20 -w '%{http_code}' ${PROTO_HEADER:+-H "$PROTO_HEADER"} "$@" || echo 000)"
  if [ "$actual" = "$expected" ]; then
    echo "ok    $description ($actual)"
  else
    echo "FAIL  $description: expected $expected, got $actual"
    failures=$((failures + 1))
  fi
}
api() { description="$1"; expected="$2"; path="$3"; shift 3; check "$description" "$expected" ${HOST_HEADER:+-H "$HOST_HEADER"} "$@" "$API_URL$path"; }

api "API is alive"                               200 /api/v1/health
api "database and Redis are reachable"           200 /api/v1/ready
api "helplines are public"                       200 /api/v1/resources
api "chat disclosure is public"                  200 /api/v1/chat/info
api "account data needs sign-in"                 401 /api/v1/auth/me
api "check-ins need sign-in"                     401 /api/v1/check-ins
api "safety plan needs sign-in"                  401 /api/v1/safety-plan
api "export needs sign-in"                       401 /api/v1/export
api "the API schema is not public"               401 /api/v1/schema
api "a forged sign-in is refused"                403 /api/v1/auth/login -X POST -H "Content-Type: application/json" -d '{}'
api "an SOS cannot be sent without sign-in"      401 /api/v1/sos/notify-contact -X POST -H "Content-Type: application/json" -d '{}'

check "the app's landing page loads"             200 "$APP_URL/"
check "Support loads without sign-in"            200 "$APP_URL/support"
check "the helplines page loads"                 200 "$APP_URL/resources"
check "the service worker is served"             200 "$APP_URL/sw.js"
check "the app proxies to the API"               200 "$APP_URL/api/v1/health"
check "the proxy does not open private data"     401 "$APP_URL/api/v1/auth/me"

# The landing page must state what the app is not.
if curl -sS -m 20 ${PROTO_HEADER:+-H "$PROTO_HEADER"} "$APP_URL/" | grep -q "not an emergency service"; then
  echo "ok    landing page states the limits"
else
  echo "FAIL  landing page does not state the limits"; failures=$((failures + 1))
fi

if [ "$failures" -gt 0 ]; then
  echo "$failures smoke test(s) failed."
  exit 1
fi
echo "All smoke tests passed."
