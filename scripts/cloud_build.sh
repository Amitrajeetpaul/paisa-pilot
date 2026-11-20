#!/usr/bin/env bash
# Run a Cloud Build and wait for it WITHOUT streaming logs. `gcloud builds submit`
# polls Cloud Build constantly and fails the whole deploy on a transient
# "Get requests per minute" 429 (low quota on a new project) even when the build
# itself succeeded. Here we submit async, then poll slowly and tolerate errors.
# usage: scripts/cloud_build.sh <project> <config> <substitutions>
set -euo pipefail
PROJECT="$1"; CONFIG="$2"; SUBS="$3"
ID=$(gcloud builds submit --async --project "$PROJECT" --config "$CONFIG" \
  --substitutions "$SUBS" --format='value(id)' .)
echo "Cloud Build started: $ID"
for _ in $(seq 1 60); do   # up to ~20 minutes
  sleep 20
  STATUS=$(gcloud builds describe "$ID" --project "$PROJECT" --format='value(status)' 2>/dev/null || echo UNKNOWN)
  echo "  build $ID: $STATUS"
  case "$STATUS" in
    SUCCESS) exit 0 ;;
    FAILURE|CANCELLED|TIMEOUT|INTERNAL_ERROR|EXPIRED) echo "Build failed: $STATUS"; exit 1 ;;
  esac
done
echo "Build did not finish in time"; exit 1
