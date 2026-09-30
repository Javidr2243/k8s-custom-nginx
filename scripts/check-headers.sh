#!/usr/bin/env sh
# Checks that a running container serves the expected security headers and behaviour.
# Usage: scripts/check-headers.sh [base_url]   (default http://127.0.0.1:8080)
set -eu

BASE="${1:-http://127.0.0.1:8080}"
fail=0

check_header() {
  path="$1"; header="$2"; expected="$3"
  value=$(curl -sS -I "$BASE$path" | tr -d '\r' | grep -i "^$header:" | head -1 | cut -d' ' -f2-)
  case "$value" in
    *"$expected"*) echo "ok   $path $header" ;;
    *) echo "FAIL $path $header: got '$value', expected to contain '$expected'"; fail=1 ;;
  esac
}

check_status() {
  method="$1"; path="$2"; expected="$3"
  code=$(curl -sS -o /dev/null -w '%{http_code}' -X "$method" "$BASE$path")
  if [ "$code" = "$expected" ]; then echo "ok   $method $path -> $code"; else echo "FAIL $method $path -> $code (expected $expected)"; fail=1; fi
}

for path in / /comparar /healthz; do
  check_header "$path" Content-Security-Policy "default-src 'none'"
  check_header "$path" Content-Security-Policy "frame-ancestors 'none'"
  check_header "$path" X-Content-Type-Options nosniff
  check_header "$path" Referrer-Policy strict-origin-when-cross-origin
  check_header "$path" Permissions-Policy "camera=()"
  check_header "$path" Cross-Origin-Opener-Policy same-origin
  check_header "$path" X-Frame-Options DENY
done

asset=$(curl -sS "$BASE/" | grep -o '/assets/[^"]*\.js' | head -1)
check_header "$asset" Cache-Control immutable
check_header "$asset" Content-Security-Policy "default-src 'none'"

check_status GET / 200
check_status GET /comparar 200
check_status POST / 405
check_status PUT / 405
check_status DELETE / 405
check_status GET /.env 404
check_status GET /.git/config 404
check_status GET /data/no-existe.json 404

if curl -sS -I "$BASE/" | tr -d '\r' | grep -qiE '^server: nginx/'; then
  echo "FAIL Server header leaks the nginx version"; fail=1
else
  echo "ok   Server header does not leak the version"
fi

exit "$fail"
