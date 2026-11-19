# Deploying Paisa Pilot to Google Cloud

This is Milestone 4 ("Ship") -- the artifacts and exact commands to deploy
for real. **Nobody has run this against a live GCP project from this
repo** -- provisioning real cloud resources is a billing action and an
explicit go-ahead from the team, not something to do unprompted. Read
this whole file, confirm the project/region/budget with the team, then
run it.

## 0. Prerequisites

- A GCP project with billing enabled. Set it:
  ```bash
  export PROJECT_ID=paisa-pilot-prod   # pick a real project id
  export REGION=asia-south1             # Mumbai -- closest to Indian users
  gcloud config set project "$PROJECT_ID"
  ```
- APIs: `gcloud services enable run.googleapis.com storage.googleapis.com firestore.googleapis.com secretmanager.googleapis.com aiplatform.googleapis.com`
- A real Gemini API key (see `ai_studio/README.md` for which models) stored
  in Secret Manager, not in any file:
  ```bash
  printf '%s' 'YOUR_KEY' | gcloud secrets create gemini-api-key --data-file=-
  ```

## 1. Cloud Storage (uploads)

```bash
export BUCKET=paisa-pilot-uploads-prod   # bucket names are globally unique
gcloud storage buckets create "gs://$BUCKET" --location="$REGION" --uniform-bucket-level-access
gcloud storage buckets update "gs://$BUCKET" --lifecycle-file=infra/cloud_storage_lifecycle.json
```

Uniform bucket-level access + no public IAM bindings means nothing is
readable except by the api service's own service account (granted below).
Server-side encryption is on by default for every GCS bucket -- nothing
to configure. See `infra/cloud_storage_lifecycle.json`'s own comment for
why the TTL is day-granular (GCS's native limit), not hour-precise.

## 2. Firestore (confirmed fields + source trail)

```bash
gcloud firestore databases create --location="$REGION" --type=firestore-native
gcloud firestore deploy --rules=infra/firestore.rules
```

## 3. Service accounts and IAM

```bash
gcloud iam service-accounts create paisa-pilot-api --display-name="Paisa Pilot API"
export SA="paisa-pilot-api@${PROJECT_ID}.iam.gserviceaccount.com"

gcloud storage buckets add-iam-policy-binding "gs://$BUCKET" \
  --member="serviceAccount:$SA" --role="roles/storage.objectAdmin"
gcloud projects add-iam-policy-binding "$PROJECT_ID" \
  --member="serviceAccount:$SA" --role="roles/datastore.user"
gcloud secrets add-iam-policy-binding gemini-api-key \
  --member="serviceAccount:$SA" --role="roles/secretmanager.secretAccessor"
```

## 4. Build and deploy the API service

From the repo root:

```bash
gcloud builds submit --tag "${REGION}-docker.pkg.dev/${PROJECT_ID}/paisa-pilot/api" \
  --config /dev/stdin <<'EOF'
steps:
  - name: gcr.io/cloud-builders/docker
    args: ['build', '-f', 'infra/api.Dockerfile', '-t', '$_IMAGE', '.']
images: ['$_IMAGE']
EOF
# (or simply: docker build -f infra/api.Dockerfile -t "$IMAGE" . && docker push "$IMAGE")

gcloud run deploy paisa-pilot-api \
  --image="${REGION}-docker.pkg.dev/${PROJECT_ID}/paisa-pilot/api" \
  --region="$REGION" \
  --service-account="$SA" \
  --set-env-vars="STORAGE_BACKEND=gcs,DB_BACKEND=firestore,READER_MODE=live,GCS_BUCKET=${BUCKET},FIRESTORE_PROJECT=${PROJECT_ID},GEMINI_PLAN_TIER=paid" \
  --set-secrets="GEMINI_API_KEY=gemini-api-key:latest" \
  --allow-unauthenticated \
  --min-instances=0 --max-instances=10

export API_URL=$(gcloud run services describe paisa-pilot-api --region="$REGION" --format='value(status.url)')
echo "API deployed at $API_URL"
```

## 5. Build and deploy the web service

The web bundle needs `$API_URL` baked in at **build** time (Vite env vars
are compiled into the static JS, not read at container runtime) -- build
the web image only after step 4 has a real `$API_URL`:

```bash
docker build -f infra/web.Dockerfile --build-arg VITE_API_BASE_URL="$API_URL" \
  -t "${REGION}-docker.pkg.dev/${PROJECT_ID}/paisa-pilot/web" .
docker push "${REGION}-docker.pkg.dev/${PROJECT_ID}/paisa-pilot/web"

gcloud run deploy paisa-pilot-web \
  --image="${REGION}-docker.pkg.dev/${PROJECT_ID}/paisa-pilot/web" \
  --region="$REGION" \
  --allow-unauthenticated \
  --min-instances=0 --max-instances=10
```

Then update the API's `ALLOWED_ORIGINS` env var to the web service's real
URL and redeploy it -- it defaults to `http://localhost:5173` for local
dev:

```bash
export WEB_URL=$(gcloud run services describe paisa-pilot-web --region="$REGION" --format='value(status.url)')
gcloud run services update paisa-pilot-api --region="$REGION" --update-env-vars="ALLOWED_ORIGINS=${WEB_URL}"
```

## 6. Verify

```bash
export WEB_URL=$(gcloud run services describe paisa-pilot-web --region="$REGION" --format='value(status.url)')
curl -s "$API_URL/healthz"
open "$WEB_URL"   # click "Try with sample data" and confirm the demo flow works
```

## Rollback

Cloud Run keeps every revision. To roll back:

```bash
gcloud run services update-traffic paisa-pilot-api --to-revisions=PREVIOUS_REVISION=100 --region="$REGION"
```

## What this doesn't cover

- A custom domain / HTTPS cert beyond Cloud Run's default `*.run.app` URL.
- CI/CD (this is a manual deploy sequence; wiring it into GitHub Actions
  or Cloud Build triggers is a roadmap item, see `docs/ROADMAP.md`).
- Sub-day upload TTL precision (see `infra/cloud_storage_lifecycle.json`).
