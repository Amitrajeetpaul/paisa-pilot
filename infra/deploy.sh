#!/usr/bin/env bash
set -euo pipefail
export PATH="/opt/homebrew/bin:$PATH"

# ==============================================================================
# Paisa Pilot - GCP Automated Deployment Script
# Reference: infra/deploy.md
# ==============================================================================

echo "=================================================="
echo "          Paisa Pilot GCP Deployment              "
echo "=================================================="

# Check for gcloud CLI
if ! command -v gcloud &> /dev/null; then
  echo "Error: 'gcloud' CLI is not installed or not in PATH."
  echo "Install it using: brew install --cask google-cloud-sdk"
  echo "Then run: gcloud auth login"
  exit 1
fi

# Ensure PROJECT_ID is set
if [ -z "${PROJECT_ID:-}" ]; then
  read -rp "Enter your GCP Project ID: " PROJECT_ID
fi

if [ -z "$PROJECT_ID" ]; then
  echo "Error: GCP Project ID is required."
  exit 1
fi

export REGION="${REGION:-asia-south1}"
export BUCKET="${BUCKET:-${PROJECT_ID}-uploads}"
export REPO_NAME="${REPO_NAME:-paisa-pilot}"

echo ""
echo "Configuration:"
echo "  Project ID: $PROJECT_ID"
echo "  Region:     $REGION"
echo "  Bucket:     gs://$BUCKET"
echo ""

gcloud config set project "$PROJECT_ID"

echo "[1/8] Enabling required GCP APIs..."
gcloud services enable \
  run.googleapis.com \
  storage.googleapis.com \
  firestore.googleapis.com \
  secretmanager.googleapis.com \
  artifactregistry.googleapis.com \
  cloudbuild.googleapis.com

echo "[2/8] Setting up Gemini API Key in Secret Manager..."
if gcloud secrets describe gemini-api-key &> /dev/null; then
  echo "Secret 'gemini-api-key' already exists."
else
  if [ -z "${GEMINI_API_KEY:-}" ]; then
    read -rsp "Enter your Gemini API Key: " GEMINI_API_KEY
    echo ""
  fi
  if [ -n "${GEMINI_API_KEY:-}" ]; then
    printf '%s' "$GEMINI_API_KEY" | gcloud secrets create gemini-api-key --data-file=-
  else
    echo "Warning: No GEMINI_API_KEY provided. Ensure 'gemini-api-key' secret exists before running live AI flows."
  fi
fi

echo "[3/8] Setting up Cloud Storage bucket for uploads..."
if ! gcloud storage buckets describe "gs://$BUCKET" &> /dev/null; then
  gcloud storage buckets create "gs://$BUCKET" --location="$REGION" --uniform-bucket-level-access
fi
gcloud storage buckets update "gs://$BUCKET" --lifecycle-file=infra/cloud_storage_lifecycle.json

echo "[4/8] Setting up Firestore (Native Mode)..."
if ! gcloud firestore databases describe &> /dev/null; then
  gcloud firestore databases create --location="$REGION" --type=firestore-native || true
fi
if command -v firebase &> /dev/null; then
  firebase deploy --only firestore:rules --project "$PROJECT_ID" || true
fi

echo "[5/8] Configuring Service Account and IAM..."
if ! gcloud iam service-accounts describe "paisa-pilot-api@${PROJECT_ID}.iam.gserviceaccount.com" &> /dev/null; then
  gcloud iam service-accounts create paisa-pilot-api --display-name="Paisa Pilot API"
fi
SA="paisa-pilot-api@${PROJECT_ID}.iam.gserviceaccount.com"

gcloud storage buckets add-iam-policy-binding "gs://$BUCKET" \
  --member="serviceAccount:$SA" --role="roles/storage.objectAdmin" --quiet
gcloud projects add-iam-policy-binding "$PROJECT_ID" \
  --member="serviceAccount:$SA" --role="roles/datastore.user" --quiet
if gcloud secrets describe gemini-api-key &> /dev/null; then
  gcloud secrets add-iam-policy-binding gemini-api-key \
    --member="serviceAccount:$SA" --role="roles/secretmanager.secretAccessor" --quiet
fi

echo "[6/8] Creating Artifact Registry repository..."
if ! gcloud artifacts repositories describe "$REPO_NAME" --location="$REGION" &> /dev/null; then
  gcloud artifacts repositories create "$REPO_NAME" \
    --repository-format=docker \
    --location="$REGION" \
    --description="Docker repository for Paisa Pilot"
fi

echo "[7/8] Building & Deploying API Service..."
API_IMAGE="${REGION}-docker.pkg.dev/${PROJECT_ID}/${REPO_NAME}/api"
gcloud builds submit \
  --substitutions="_TAG=${API_IMAGE}" \
  --config=/dev/stdin <<'EOF'
steps:
  - name: 'gcr.io/cloud-builders/docker'
    args: ['build', '-f', 'infra/api.Dockerfile', '-t', '${_TAG}', '.']
images: ['${_TAG}']
EOF

gcloud run deploy paisa-pilot-api \
  --image="$API_IMAGE" \
  --region="$REGION" \
  --service-account="$SA" \
  --set-env-vars="STORAGE_BACKEND=gcs,DB_BACKEND=firestore,READER_MODE=live,GCS_BUCKET=${BUCKET},FIRESTORE_PROJECT=${PROJECT_ID},GEMINI_PLAN_TIER=paid" \
  --set-secrets="GEMINI_API_KEY=gemini-api-key:latest" \
  --allow-unauthenticated \
  --min-instances=0 --max-instances=10

API_URL=$(gcloud run services describe paisa-pilot-api --region="$REGION" --format='value(status.url)')
echo "API deployed at: $API_URL"

echo "[8/8] Building & Deploying Web Service (baking in API_URL)..."
WEB_IMAGE="${REGION}-docker.pkg.dev/${PROJECT_ID}/${REPO_NAME}/web"
gcloud builds submit \
  --substitutions="_TAG=${WEB_IMAGE},_API_URL=${API_URL}" \
  --config=/dev/stdin <<'EOF'
steps:
  - name: 'gcr.io/cloud-builders/docker'
    args: ['build', '-f', 'infra/web.Dockerfile', '--build-arg', 'VITE_API_BASE_URL=$_API_URL', '-t', '${_TAG}', '.']
images: ['${_TAG}']
EOF

gcloud run deploy paisa-pilot-web \
  --image="$WEB_IMAGE" \
  --region="$REGION" \
  --allow-unauthenticated \
  --min-instances=0 --max-instances=10

WEB_URL=$(gcloud run services describe paisa-pilot-web --region="$REGION" --format='value(status.url)')

echo "Updating API CORS with web origin: $WEB_URL..."
gcloud run services update paisa-pilot-api --region="$REGION" --update-env-vars="ALLOWED_ORIGINS=${WEB_URL}"

echo ""
echo "=================================================="
echo "Deployment Complete!"
echo "API URL: $API_URL"
echo "Web URL: $WEB_URL"
echo "=================================================="
curl -s "${API_URL}/healthz" && echo ""
echo "Open $WEB_URL in your browser to start using Paisa Pilot."
