#!/usr/bin/env bash
#
# Rent vs Buy — Deploy script (run after setup-aws.sh)
# Builds frontend, uploads to S3, invalidates CloudFront, deploys API.
#
# Usage:
#   ./deploy/deploy.sh              # deploy both frontend + backend
#   ./deploy/deploy.sh frontend     # frontend only
#   ./deploy/deploy.sh backend      # backend only
#   ./deploy/deploy.sh invalidate   # just invalidate CloudFront cache

set -euo pipefail

STATE_FILE="deploy/.aws-state"
state_get() { grep "^$1=" "$STATE_FILE" 2>/dev/null | cut -d= -f2- || echo ""; }

DOMAIN="rentbuysellapp.com"
BUCKET_NAME="rentbuysellapp.com"
CF_DIST_ID=$(state_get CF_DIST_ID)
EIP=$(state_get EC2_IP)
[[ -z "$EIP" ]] && EIP=$(state_get EIP)
KEY_FILE="deploy/rentbuy-key.pem"

if [[ ! -f "$STATE_FILE" ]]; then
  echo "ERROR: No state file found. Run ./deploy/setup-aws.sh first."
  exit 1
fi

log() { echo ""; echo "── $1"; }

# ─────────────────────────────────────────────────────────────────────
deploy_frontend() {
  log "Building frontend"
  cd web
  NEXT_PUBLIC_API_URL="https://api.$DOMAIN" npm run build
  cd ..

  log "Uploading to S3"
  aws s3 sync web/out/ "s3://$BUCKET_NAME" --delete --size-only
  echo "  ✓ Uploaded $(find web/out -type f | wc -l | tr -d ' ') files"

  log "Invalidating CloudFront cache"
  if [[ -n "$CF_DIST_ID" ]]; then
    INVALIDATION_ID=$(aws cloudfront create-invalidation \
      --distribution-id "$CF_DIST_ID" \
      --paths "/*" \
      --query 'Invalidation.Id' --output text)
    echo "  ✓ Invalidation: $INVALIDATION_ID (takes 1-2 minutes to propagate)"
  else
    echo "  ⚠ No CloudFront distribution ID found, skipping invalidation"
  fi
}

# ─────────────────────────────────────────────────────────────────────
deploy_backend() {
  if [[ -z "$EIP" ]]; then
    echo "ERROR: No EC2 IP found in state file."
    exit 1
  fi

  log "Deploying API to EC2 ($EIP)"

  # Sync code (excluding data dir and __pycache__)
  rsync -avz --delete \
    --exclude 'data/' \
    --exclude '__pycache__/' \
    --exclude '.pytest_cache/' \
    --exclude '*.pyc' \
    -e "ssh -i $KEY_FILE -o StrictHostKeyChecking=no" \
    api/ "ec2-user@$EIP:~/mortgage/api/"

  echo "  ✓ Code synced"

  # Restart service
  ssh -i "$KEY_FILE" -o StrictHostKeyChecking=no "ec2-user@$EIP" \
    "sudo systemctl restart rentbuy && sleep 2 && curl -sf http://localhost:8000/health"

  echo "  ✓ Service restarted, health check passed"
}

# ─────────────────────────────────────────────────────────────────────
invalidate_only() {
  if [[ -n "$CF_DIST_ID" ]]; then
    aws cloudfront create-invalidation --distribution-id "$CF_DIST_ID" --paths "/*" > /dev/null
    echo "✓ CloudFront invalidation created"
  else
    echo "ERROR: No CloudFront distribution ID"
    exit 1
  fi
}

# ─────────────────────────────────────────────────────────────────────
upload_data() {
  if [[ -z "$EIP" ]]; then
    echo "ERROR: No EC2 IP found."
    exit 1
  fi

  log "Uploading market.db to EC2"
  scp -i "$KEY_FILE" -o StrictHostKeyChecking=no \
    api/data/market.db "ec2-user@$EIP:~/mortgage/api/data/"
  echo "  ✓ market.db uploaded ($(du -h api/data/market.db | cut -f1))"
}

# ─────────────────────────────────────────────────────────────────────
case "${1:-all}" in
  frontend)   deploy_frontend ;;
  backend)    deploy_backend ;;
  invalidate) invalidate_only ;;
  data)       upload_data ;;
  all)
    deploy_frontend
    deploy_backend
    echo ""
    echo "══════════════════════════════════════════════"
    echo "  Deploy complete!"
    echo "  Frontend: https://$DOMAIN"
    echo "  API:      https://api.$DOMAIN/health"
    echo "══════════════════════════════════════════════"
    ;;
  *)
    echo "Usage: $0 [frontend|backend|invalidate|data|all]"
    exit 1
    ;;
esac
