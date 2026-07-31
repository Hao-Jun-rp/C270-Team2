#!/usr/bin/env bash
#
# Sparkle production deploy
# -------------------------
# Pulls the CI-built image and starts the container with secrets fetched from
# AWS SSM Parameter Store at deploy time. No .env file on disk.
#
# The instance authenticates using its attached IAM role
# (SparkleProdInstanceRole) via the EC2 metadata service — there are no AWS
# access keys anywhere on this machine.
#
# Usage:
#   ./deploy.sh                # deploy :latest
#   ./deploy.sh <tag>          # deploy a specific tag, e.g. a commit SHA
#
set -euo pipefail

IMAGE="c270sparkleteam2/sparkle"
TAG="${1:-latest}"
REGION="ap-southeast-1"
PARAM_PREFIX="/sparkle/prod"
CONTAINER="sparkle"
PORT=8000
CERTS_DIR="$HOME/sparkle/certs"

echo "==> Deploying ${IMAGE}:${TAG}"

# --- 1. Confirm we can actually authenticate before changing anything -------
echo "==> Checking instance identity"
aws sts get-caller-identity --region "$REGION" --query Arn --output text

# --- 2. Fetch secrets from Parameter Store ---------------------------------
# --with-decryption asks SSM to decrypt the SecureString values. This is the
# call that requires kms:Decrypt in the instance role's policy.
echo "==> Fetching secrets from SSM (${PARAM_PREFIX})"

get_param() {
  aws ssm get-parameter \
    --name "${PARAM_PREFIX}/$1" \
    --with-decryption \
    --query "Parameter.Value" \
    --output text \
    --region "$REGION"
}

SECRET_KEY="$(get_param SECRET_KEY)"
DATABASE_URL="$(get_param DATABASE_URL)"

# Fail loudly rather than starting a broken container with empty config.
if [[ -z "$SECRET_KEY" || -z "$DATABASE_URL" ]]; then
  echo "ERROR: a required parameter came back empty. Aborting." >&2
  exit 1
fi
echo "    got SECRET_KEY (${#SECRET_KEY} chars) and DATABASE_URL (${#DATABASE_URL} chars)"

# --- 3. Pull the image -----------------------------------------------------
echo "==> Pulling image"
docker pull "${IMAGE}:${TAG}"

# --- 4. Replace the running container --------------------------------------
echo "==> Restarting container"
docker stop "$CONTAINER" 2>/dev/null || true
docker rm   "$CONTAINER" 2>/dev/null || true

docker run -d \
  --name "$CONTAINER" \
  --restart unless-stopped \
  -p "${PORT}:8000" \
  -e SECRET_KEY="$SECRET_KEY" \
  -e DATABASE_URL="$DATABASE_URL" \
  -e MYSQL_SSL_CA="/app/certs/aiven-ca.pem" \
  -e SESSION_COOKIE_SECURE="1" \
  -v "${CERTS_DIR}:/app/certs:ro" \
  "${IMAGE}:${TAG}"

# Don't leave the plaintext values sitting in this shell any longer than needed.
unset SECRET_KEY DATABASE_URL

# --- 5. Wait for the app, then verify --------------------------------------
# gunicorn takes a few seconds to boot; curling immediately returns 502.
echo "==> Waiting for the app to answer"
for i in {1..15}; do
  code="$(curl -s -o /dev/null -w '%{http_code}' "http://localhost:${PORT}/listings" || true)"
  if [[ "$code" == "200" ]]; then
    echo "    healthy after ${i}s (HTTP $code)"
    echo "==> Deploy OK: ${IMAGE}:${TAG}"
    exit 0
  fi
  sleep 1
done

echo "ERROR: app did not return 200 within 15s (last code: ${code:-none})" >&2
echo "       check: docker logs ${CONTAINER} --tail 50" >&2
exit 1
