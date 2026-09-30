#!/usr/bin/env bash
# Pull-based deployment. Runs on the VPS from a systemd timer as the "gdmty-deploy" user.
#  1. Resolve the digest of the "prod" tag on GHCR (moved by CI after approval).
#  2. Verify with cosign that the image was signed by this repo's CI workflow on main.
#  3. Start it pinned by digest, wait for the healthcheck and roll back if it fails.
# Takes no arguments (the SSH key / timer cannot pass anything to it).
set -euo pipefail
umask 077

IMAGE="ghcr.io/javidr2243/k8s-custom-nginx"
IDENTITY_RE='^https://github\.com/javidr2243/k8s-custom-nginx/\.github/workflows/ci\.yml@refs/heads/main$'
ISSUER="https://token.actions.githubusercontent.com"
APP_DIR="/opt/gdmty"
STATE_DIR="/var/lib/gdmty-deploy"
COMPOSE=(docker compose --project-directory "$APP_DIR" -f "$APP_DIR/docker-compose.yml" --env-file "$APP_DIR/.env")

log() { printf '%s %s\n' "$(date -u +%FT%TZ)" "$*"; }

if [[ $# -ne 0 ]]; then
  log "este script no acepta argumentos" >&2
  exit 2
fi
mkdir -p "$STATE_DIR"
exec 9>"$STATE_DIR/lock"
flock -n 9 || { log "otro despliegue en curso"; exit 0; }

digest="$(docker buildx imagetools inspect "$IMAGE:prod" --format '{{json .Manifest.Digest}}' | tr -d '"')"
if [[ ! "$digest" =~ ^sha256:[0-9a-f]{64}$ ]]; then
  log "digest inválido: '$digest'" >&2
  exit 1
fi
current="$(cat "$STATE_DIR/current" 2>/dev/null || true)"
if [[ "$digest" == "$current" ]]; then
  exit 0
fi

log "nuevo digest $digest; verificando firma"
if ! cosign verify \
  --certificate-identity-regexp "$IDENTITY_RE" \
  --certificate-oidc-issuer "$ISSUER" \
  "$IMAGE@$digest" >/dev/null; then
  log "FIRMA NO VÁLIDA para $IMAGE@$digest: no se despliega" >&2
  exit 1
fi

set_image() {
  local d="$1" base
  base="$(grep -v '^APP_IMAGE=' "$APP_DIR/.env" || true)"
  printf '%s\nAPP_IMAGE=%s@%s\n' "$base" "$IMAGE" "$d" >"$APP_DIR/.env.tmp"
  mv "$APP_DIR/.env.tmp" "$APP_DIR/.env"
}

set_image "$digest"
if "${COMPOSE[@]}" up -d --wait --wait-timeout 90 app caddy; then
  echo "$digest" >"$STATE_DIR/current"
  { echo "$digest"; cat "$STATE_DIR/history" 2>/dev/null || true; } | awk '!seen[$0]++' | head -n 3 >"$STATE_DIR/history.tmp"
  mv "$STATE_DIR/history.tmp" "$STATE_DIR/history"
  docker image prune -f --filter "label=org.opencontainers.image.title=adonde-va-tu-dinero-mty" >/dev/null || true
  log "desplegado $digest"
else
  log "el healthcheck falló; regresando a ${current:-(ninguno)}" >&2
  if [[ -n "$current" ]]; then
    set_image "$current"
    "${COMPOSE[@]}" up -d --wait --wait-timeout 90 app caddy || true
  fi
  exit 1
fi
