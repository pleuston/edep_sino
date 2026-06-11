# EDEp Sino

TEI Publisher 10 (Jinks-generated) application for **Chinese epigraphy**, built on eeditiones' EDEp. Edits EpiDoc TEI inscriptions directly in the browser via Fore forms.

## Branch policy

- **`sino-tp10`** — the working branch (this one). Based on `upstream/edep-jinks` (the TP10/Jinks port of EDEp).
- **`master`** — pristine mirror of `upstream/master` (classic EDEp). Never develop here.
- Tag **`editor-port-src`** = `upstream/altered-model` — the modernized editor (Fore 3.1.x, modular parts, fragments-as-separate-docs model) that was ported into this app. Diff against it when porting fixes.
- Upstream sync: `git fetch upstream && git merge upstream/edep-jinks` (merge, never rebase). Log every sync in `doc/UPSTREAM.md`.

## Jinks discipline (keeps the app regenerable)

`.jinks.json` / `.jinks-versions.json` are the generator's SHA-256 manifest — **never hand-edit them**. Files unknown to the manifest (everything sino-specific) are never touched by the generator; edited generated files are flagged, not overwritten. Run the generator only for config-driven changes (theme/menu/odds/languages); code arrives via git merges.

## Build & deploy

```sh
ant                  # plain xar (no npm assets) → build/edep-sino-1.0.0.xar
ant xar-local        # npm install + bundle pb-components/fore assets + xar  ← use this one
# data package:
cd data-pkg && ant   # → build/edep-sino-data-*.xar
```

Local eXist: `docker start edep-sino-db` (eXist 6.2 on :8080, admin / empty password — see `doc/INSTALL.md`).
Deploy a xar: upload via `http://localhost:8080/exist/apps/dashboard/` or the REST API (commands in `doc/INSTALL.md`).
App URL: `http://localhost:8080/exist/apps/edep-sino/` · Data app: `/db/apps/edep-sino-data`.

## Tests

```sh
npx cypress run                          # full e2e suite (eXist must be running with app+data deployed)
npx cypress run --spec 'test/cypress/e2e/api/*'
```

The lossless save→reopen roundtrip spec is the regression keystone — keep it green.

## Documentation map

`doc/ARCHITECTURE.md` (structure) · `doc/INSTALL.md` (bring-up) · `doc/DEVELOPMENT.md` (how to extend) · `doc/sino-model.md` (Chinese EpiDoc encoding decisions — the contract for all sino fields) · `doc/USER-GUIDE.md` (for epigraphers) · `doc/UPSTREAM.md` (sync log) · `doc/DEPLOYMENT.md` (production).

When adding/changing features, update the matching doc in the same commit.
