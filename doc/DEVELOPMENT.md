# EpiWen — Development guide

## Repository layout

Two installable packages live in this repo: the **application** (root) and the **data package** (`data-pkg/`) — see `doc/ARCHITECTURE.md`. Branch policy and upstream sync: `doc/UPSTREAM.md`. Local bring-up: `doc/INSTALL.md`.

## Build system

```sh
ant xar-local        # full app build: npm install assets + xar (use this)
ant                  # bare xar without node assets (CI-style, assets must exist)
cd data-pkg && ant   # data package xar
```

`ant xar-local` copies into the build:
- pb-components dist/css/lib/i18n → `resources/{lib,css,images,i18n/common}`
- Fore (`@jinntec/fore`): `dist/*.js` → `resources/lib/`, `resources/*.css` → `resources/css/`
- jinn-codemirror: `dist/jinn-codemirror-bundle.js*` + `tei.json` → `resources/scripts/`
- pico.css → `resources/styles/`

### Fast iteration without rebuilding

Any file already deployed can be synced straight into the running eXist:

```sh
curl -s -u admin: -T templates/edit.html -H 'Content-Type: text/html' \
  http://localhost:8080/exist/rest/db/apps/epiwen/templates/edit.html
```

Templates are recompiled per request — no restart needed. (XQuery modules under `modules/` are cached per compilation; re-PUT triggers recompile.)

## How a page works (jinks-templates)

Pages are `templates/{name}.html`, served at `/{name}.html` via `modules/lib/api/view.xql` (`vapi:html`). A page is a `<template>` root with a JSON front matter block:

```
---json
{ "templating": {"extends": "templates/layouts/base.html"},
  "styles": [...], "script": {"custom": [...]} }
---
```

- `[% template NAME %]…[% endtemplate %]` fills the layout's `[% block NAME %]` (e.g. `scripts`, `styles`, `hero`); remaining content fills `[% block content %]`.
- Expressions: `[[ $context-path ]]` (app URL), `[[ page:parameter($context, 'id', '') ]]` (query parameter with default).
- `[% include "templates/parts/edit/x.html" %]` splices a fragment.
- Literal `{ … }` braces pass through untouched (the engine escapes them) — Fore AVT expressions like `url="api/inscription?id={instance('params')/id}"` are safe.

## The editor (`templates/edit.html`)

Ported from upstream `altered-model` (tag `editor-port-src`); the Fore form edits the EpiDoc XML directly in the browser.

| Piece | Location |
|---|---|
| Page (model + submissions + section nav) | `templates/edit.html` (`/edit.html?collection=workspace[&id=…]`) |
| Form sections (one `<details>` each) | `templates/parts/edit/*.html` |
| Blank EpiDoc skeleton / repeatable snippets | `templates/fore/epidoc-template.xml`, `templates/fore/templates.xml` |
| Geo picker subform (loaded by `fx-control/@src`) | `templates/geo-picker.html` |
| XML micro-editors (jinn-codemirror wrapper) | `resources/scripts/edep-xml-editor.js` (+ `tei.json` schema) |
| Icons (`<edep-icon name="…">`, replaces iron-icon) | `resources/scripts/edep-icons.js` |
| Editor layout/styling on top of pico + jinks grid | `resources/css/edit.css` (+ inherited `edep-theme*.css`) |

**Conventions when touching the editor:**
- Controlled vocabularies load as `fx-instance src="../epiwen-data/data/taxonomy/{name}.xml"` with `xpath-default-namespace` TEI; the files are TEI `<taxonomy>` docs (`category/@corresp` + `catDesc/@xml:lang`) — except `country.xml`/`province.xml`, which the geo-picker consumes as legacy `<vocabulary>/<term @xml:id>/<name @xml:lang>`.
- Every element/attribute a control binds to **must exist (possibly empty) in `epidoc-template.xml`** — missing nodes hide their controls by design.
- pico.css styles every `nav ul` as a horizontal flexbox — scope editor overrides in `edit.css`.

### Adding a form field
1. Add the (empty) element/attribute to `templates/fore/epidoc-template.xml` (and `templates.xml` if repeatable).
2. Add an `fx-control`/`fx-repeat` to the relevant `templates/parts/edit/*.html` with `<pb-i18n>` labels.
3. Add the i18n keys to `resources/i18n/app/{en,de,zh}.json`.
4. If it needs a vocabulary: drop a taxonomy XML into `data-pkg/data/taxonomy/`, declare the `fx-instance` in `templates/edit.html`.
5. Extend the cypress roundtrip fixture so save→reopen covers the new node.

## API surface

Three OpenAPI specs are routed by roaster: `modules/lib/api.json` (TEI Publisher base), `modules/registers-api.json` (registers), `modules/custom-api.json` (**ours** — editor + sino routes land here). Custom implementations: `modules/custom-api.xql`. Re-PUT of a JSON spec requires re-deploy or touching the router (install does this).

## Tests

```sh
npx cypress run                       # all (eXist + app + data deployed)
npx cypress run --spec 'test/cypress/e2e/gui/editor.cy.js'
```

`test/cypress/e2e/gui/editor.cy.js` guards the editor render (Fore init, taxonomy loading, console-error-free). From M3 the inscription roundtrip spec is the regression keystone. Screenshots land in `test/cypress/screenshots/`.

## Jinshi import pipeline

```sh
# Re-import from the vault (vault is read-only; script is idempotent):
python3 scripts/import-jinshi.py \
  --vault /Users/sassmann/Documents/obsidian-vault \
  --id-map scripts/jinshi-id-map.json \
  --out-works  data-pkg/data/registers/works.xml \
  --out-jinshi data-pkg/data/registers/jinshi.xml \
  --out-persons data-pkg/data/registers/persons.xml \
  --report scripts/jinshi-import-report.md

# Re-run produces byte-identical XML if vault is unchanged (idempotency check).
# After import: build and deploy data package, then reindex:
cd data-pkg && ant
# deploy epiwen-data-*.xar via REST, then:
curl -u admin: --data-urlencode '_query=xmldb:reindex("/db/apps/epiwen-data/data")' \
  http://localhost:8080/exist/rest/db
```

New ids are appended to `scripts/jinshi-id-map.json` (committed). Hand-seeded ids (`work-000001`, `work-000002`, `insc-000001`, etc.) are pre-registered there; the importer merges rather than duplicates. Import report at `scripts/jinshi-import-report.md` lists parse rates, unresolved links, and unparsed attestation lines.

## Adding a new register type

Checklist (pattern: the `inscription` type added in M-J1):

1. **Config**: add entry to `$config:register-map` in `modules/config.xqm` (`id`, `prefix`, `type-name`, `root-element`).
2. **Register doc**: create `data-pkg/data/registers/{type}.xml` with a top-level `standOff` element and the list element (`listObject`, `listBibl`, etc.) bearing the register `@xml:id`.
3. **`registers.xql`**: add `case element(tei:{element})` to `rapi:prepare-record`, `rapi:insert-point`, `rapi:next`, and `rapi:save`.
4. **`registers-api.json`/`.xql`**: add browse (`/{type}`, `/{type}/{id}`) and API (`/api/{type}`, `/api/{type}/all`) routes; implement `rview:{type}-categories` and `rview:{type}-all`.
5. **Templates**: `templates/{types}.html` (list) + `templates/{type}.html` (detail) — clone the place pair.
6. **ODD**: add element overrides in `resources/odd/output.odd`; recompile via `POST /api/odd`.
7. **Lucene**: `data-pkg/collection.xconf` — add fields for the new element type; reindex.
8. **i18n**: add keys under `registers.{type}` in `resources/i18n/app/{en,de,zh_TW}.json`.
9. **Menu**: add to `context.json` menu.items (under `registers` subitems or top-level).
10. **Tests**: api spec (`PUT {type}-NEW` assigns real id) + gui spec (list renders, detail renders, joins work).

## Known cosmetic issues (tracked for the polish milestone)

- The top menu wraps long entries character-by-character (`menu.css` column sizing) — app-global, not editor-specific.
