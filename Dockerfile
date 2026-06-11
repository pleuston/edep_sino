# =============================================================================
# EDEp Sino — production image
# Build:  docker build -t edep-sino .
# Run:    docker compose up   (or: docker run -p 8080:8080 edep-sino)
# =============================================================================

# ---- builder: compile both XAR packages --------------------------------
FROM node:22-bookworm AS builder

RUN apt-get update && apt-get install -y --no-install-recommends ant && rm -rf /var/lib/apt/lists/*

# library dependencies (versions verified against this app, doc/INSTALL.md)
ARG ROASTER_VERSION=1.12.1
ARG TPLIB_VERSION=6.1.0
ARG JINKS_TEMPLATES_VERSION=1.4.1
RUN mkdir -p /xars \
    && curl -sL -o /xars/001-roaster.xar \
        https://github.com/eeditiones/roaster/releases/download/v${ROASTER_VERSION}/roaster-${ROASTER_VERSION}.xar \
    && curl -sL -o /xars/002-jinks-templates.xar \
        https://github.com/eeditiones/jinks-templates/releases/download/v${JINKS_TEMPLATES_VERSION}/jinks-templates.xar \
    && curl -sL -o /xars/003-tei-publisher-lib.xar \
        https://github.com/eeditiones/tei-publisher-lib/releases/download/v${TPLIB_VERSION}/tei-publisher-lib.xar

WORKDIR /build
COPY . .
RUN npm install --no-audit --no-fund \
    && ant xar-local \
    && (cd data-pkg && ant) \
    && cp data-pkg/build/edep-sino-data-*.xar /xars/004-edep-sino-data.xar \
    && cp build/edep-sino-*.xar /xars/005-edep-sino.xar

# ---- runtime: eXist with everything autodeployed ------------------------
# eXist autodeploys /exist/autodeploy in lexicographic order; the numeric
# prefixes guarantee libraries -> data package -> application.
FROM existdb/existdb:6.4.0

COPY --from=builder /xars/*.xar /exist/autodeploy/

EXPOSE 8080

HEALTHCHECK --interval=30s --timeout=5s --start-period=120s --retries=5 \
    CMD java -version >/dev/null 2>&1 && exec 3<>/dev/tcp/localhost/8080 && echo -e 'GET /exist/ HTTP/1.0\n' >&3 && head -1 <&3 | grep -q 'HTTP' || exit 1
