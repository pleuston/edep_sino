# EDEp Sino — Local installation

Verified procedure (macOS / Apple Silicon, June 2026). Production deployment: see `doc/DEPLOYMENT.md`.

## Prerequisites

| Tool | Install | Notes |
|---|---|---|
| Java + ant | `brew install ant` | pulls OpenJDK |
| Node.js + npm | `brew install node` | for build + cypress |
| Docker runtime | `brew install colima docker && colima start --cpu 2 --memory 4` | any Docker works; Colima is CLI-only |

## 1. Start eXist-db

```sh
docker run -dit -p 8080:8080 --name edep-sino-db existdb/existdb:6.4.0
# wait until it answers (first boot ≈ 1 min):
curl -s -o /dev/null -w '%{http_code}\n' http://localhost:8080/exist/   # → 302
```

**Use 6.4.0, not 6.2.0**: the 6.2.0 image is amd64-only and crawls under emulation on Apple Silicon; 6.4.0 is multi-arch (native arm64) and satisfies the app's `semver-min 6.2.0`. Admin password of a fresh container is empty.

## 2. Download library dependencies

```sh
mkdir -p /tmp/xars && cd /tmp/xars
curl -sL -O https://github.com/eeditiones/roaster/releases/download/v1.12.1/roaster-1.12.1.xar
curl -sL -O https://github.com/eeditiones/tei-publisher-lib/releases/download/v6.1.0/tei-publisher-lib.xar
curl -sL -O https://github.com/eeditiones/jinks-templates/releases/download/v1.4.1/jinks-templates.xar
```

Tested versions: roaster **1.12.1**, tei-publisher-lib **6.1.0** (all EDEp ODDs compile under it), jinks-templates **1.4.1**.

## 3. Build the two app packages

```sh
cd <repo>            # application: npm assets (pb-components, fore, pico) + xar
npm install
ant xar-local        # → build/edep-sino-1.0.0.xar

cd data-pkg && ant   # data package → data-pkg/build/edep-sino-data-0.1.0.xar
```

## 4. Install (order matters)

The data package must be installed **before** the app: the app's configuration eagerly reads `taxonomy.xml` and the `registers/` collection from `/db/apps/edep-sino-data/data` at import time, and post-install compiles the ODDs.

```sh
deploy() {
  f=$1; n=$(basename "$f")
  curl -s -u admin: -X PUT --data-binary @"$f" -H 'Content-Type: application/octet-stream' \
    "http://localhost:8080/exist/rest/db/xars/$n" > /dev/null
  curl -s -u admin: --data-urlencode "_query=repo:install-and-deploy-from-db('/db/xars/$n')" \
    --data-urlencode "_wrap=no" "http://localhost:8080/exist/rest/db"; echo
}
deploy /tmp/xars/roaster-1.12.1.xar
deploy /tmp/xars/jinks-templates.xar
deploy /tmp/xars/tei-publisher-lib.xar
deploy data-pkg/build/edep-sino-data-0.1.0.xar
deploy build/edep-sino-1.0.0.xar
```

Each call must answer `<status … result="ok"/>`.

**Re-deploying after changes**: same `deploy` call; for the data package remove first
(`_query=repo:remove('https://jinntec.de/apps/edep-sino-data')`) — its install scripts assume a fresh target.

## 5. Smoke test

```sh
open http://localhost:8080/exist/apps/edep-sino/        # landing page
# ODD compilation produced the transforms?
curl -s -u admin: --data-urlencode \
  "_query=count(xmldb:get-child-resources('/db/apps/edep-sino/transform'))" \
  --data-urlencode "_wrap=no" http://localhost:8080/exist/rest/db   # ≈ 38
# e2e suite:
npx cypress run
```

Login user for editing/tests: `tei` / `simple` (created on app install from `repo.xml`).

## What lives where

| URL / path | What |
|---|---|
| `http://localhost:8080/exist/apps/edep-sino/` | the application |
| `/db/apps/edep-sino-data/data/workspace` | inscriptions |
| `/db/apps/edep-sino-data/data/taxonomy/*.xml` | controlled vocabularies |
| `/db/apps/edep-sino-data/data/registers/` | person/place/bibliography registers |
| `/db/apps/edep-sino-data/data/landing/landing.xml` | landing page content |
| `/db/apps/edep-sino/transform/` | compiled ODD transforms (regenerated on install) |

## Known quirks

- `POST /api/login` without credentials answers `200` with the guest session (roaster behavior) — not `401`.
- The container has no shell; read logs with `docker logs edep-sino-db` or `docker cp edep-sino-db:/exist/logs/exist.log .`.
