# JARVIS Command Center on Railway — one service: Brain (FastAPI) + built UI.
# UI: clone public conrad-command-center @ main during build (Iron Man HUD on main).
# Runtime layout matches Manus/docker: /app/goldfront-os + /app/conrad-command-center/dist
# (see brain/main.py _COMMAND_CENTER_DIST).

FROM node:20-bookworm-slim AS ui

RUN apt-get update \
  && apt-get install -y --no-install-recommends git ca-certificates \
  && rm -rf /var/lib/apt/lists/*

ARG CONRAD_COMMAND_CENTER_REPO=https://github.com/lindsey-creator/conrad-command-center.git
ARG CONRAD_COMMAND_CENTER_REF=main
# Railway HUD_BUILD must be an ARG in this RUN or Docker reuses a stale HUD clone.
ARG HUD_BUILD=dev

WORKDIR /build
RUN echo "HUD clone ${CONRAD_COMMAND_CENTER_REF} build=${HUD_BUILD}" \
  && git clone --depth 1 --branch "${CONRAD_COMMAND_CENTER_REF}" \
  "${CONRAD_COMMAND_CENTER_REPO}" conrad-command-center

WORKDIR /build/conrad-command-center
RUN npm ci && npm run build

FROM python:3.11-slim AS runtime

WORKDIR /app

COPY requirements.txt ./goldfront-os/requirements.txt
RUN pip install --no-cache-dir -r goldfront-os/requirements.txt

COPY . ./goldfront-os/
COPY --from=ui /build/conrad-command-center/dist ./conrad-command-center/dist

WORKDIR /app/goldfront-os

ENV GOLDFRONT_OWNER=lindsey
ENV PYTHONUNBUFFERED=1
# Railway public domains are bound to 8000; keep PORT=8000 in the service too.
ENV PORT=8000

EXPOSE 8000

# Railway injects PORT; default 8000 if unset.
CMD ["sh", "-c", "exec uvicorn brain.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
