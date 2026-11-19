# Build from the REPO ROOT (so this stage can also pull in infra/nginx.conf.template):
#   docker build -f infra/web.Dockerfile --build-arg VITE_API_BASE_URL=https://paisa-pilot-api-xxxxx.a.run.app -t paisa-pilot-web .
# VITE_API_BASE_URL must be the api Cloud Run service's URL -- Vite bakes
# env vars into the static bundle at build time, so this has to be known
# before building, not set as a runtime env var on the deployed container.
# See infra/deploy.md for the full sequence (api gets deployed first).

FROM node:22-slim AS build
WORKDIR /app
COPY web/package.json web/package-lock.json ./
RUN npm ci
COPY web/ .
ARG VITE_API_BASE_URL
ENV VITE_API_BASE_URL=${VITE_API_BASE_URL}
RUN npm run build

FROM nginx:1.27-alpine
COPY --from=build /app/dist /usr/share/nginx/html
COPY infra/nginx.conf.template /etc/nginx/templates/default.conf.template

# Cloud Run sets $PORT (default 8080); nginx's official image substitutes
# any $VAR in /etc/nginx/templates/*.template into /etc/nginx/conf.d/ on
# startup, which is how a single image works at any PORT Cloud Run assigns.
ENV PORT=8080
EXPOSE 8080
