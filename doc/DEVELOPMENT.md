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

**Template-expression gotchas (each causes a generic "Ooops" page; both bit M-S1):**
- **Output `string()`, not the node.** `[[ $x/@attr ]]` or `[[ $x/tei:foo ]]` in *element content* emits an attribute/element node and throws `XQTY0024: An attribute node cannot follow a node that is not an element` the moment the data hits that path (so it can lurk until one record has the field). Always `[[ $x/@attr/string() ]]`. In a quoted attribute (`href="[[ … ]]"`) the node is fine (string-interpolated).
- **No bare leading-paren sequences.** `[% if (a, b) != '' %]` or `[[ ($a?route, 'x')[1] ]]` break the jinks expression parser ("expected char: '&'"). Use predicate/function forms instead: `[% if $x[@a or @b] %]`, `[[ head(($a?route, 'x')) ]]`, `gt` instead of `>`. Because `templating.use` (e.g. `metadata-blocks.html`) runs on **every** page, one bad expression there 500s the whole site.

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

## Stone-sutra import pipeline (sutras-data → sutras register)

Imports the **stonesutras.org** dataset (real catalog + TEI XML, not markdown) into the
separate **Stone Sutras** register. Pilot is per-site; see `doc/sino-model.md` §"Stone Sutras corpus".

```sh
# Source = the stonesutras.org eXist data tree; one site at a time (idempotent):
python3 scripts/import-sutras-data.py \
  --source /Users/sassmann/Documents/sutras-data \
  --site HDS                       # Hongdingshan (洪頂山)

# Writes (per site):
#   data-pkg/data/registers/sutras.xml        — <object type="sutra"> authority records
#   data-pkg/data/registers/places.xml        — site merged in (register cross-ref store)
#   data-pkg/data/places/place-<site>.xml     — per-place file (/api/places + map store)
#   data-pkg/data/workspace/<catalog-id>.xml  — full EpiDoc editions (the transcriptions)
#   scripts/sutras-id-map.json                — stable sutra-NNNNNN ids (committed)
#   scripts/sutras-import-report.md           — per-inscription table + missing-doc log

# Gate every generated edition BEFORE deploying (hard requirement):
sh scripts/validate-epidoc.sh data-pkg/data/workspace/HDS_*.xml   # all must say "ok:"

# Fixture test (id stability + idempotency + gate-valid editions):
python3 scripts/test_import_sutras_data.py
```

Deploy = REST PUT the changed app files (`config.xqm`, `registers.xql`, `registers-api.{xql,json}`,
`context.json`, i18n, `templates/sutra{,s}.html`, taxonomy) and data files (`sutras.xml`,
`places.xml`, `places/place-*.xml`, `workspace/*.xml`), restore `tei` ownership on the data
files (see permissions note below), then reindex. The roaster router only re-registers the new
`/sutras` routes after the spec is re-PUT **and** the router module is touched (re-PUT
`modules/lib/api.xql`).

> **Gotcha (fixed in M-S1):** imported editions carry non-`E` `idno[@type='EDEp']` (e.g. `HDS_11`).
> `custom-api.xql`'s new-EDEp-id query now filters `[matches(., '^E\d+$')]` so they don't poison
> the `E0000001…` sequence. And `registers.xql` `rapi:save` read `$id` before it was bound (a
> latent break from the rubbings commit, affecting **all** register CRUD) — now reordered.

## Data permissions (why editor saves 500)

The editor saves as `tei`/simple via `xmldb:store`, so the data collections must be **`tei:tei`, group-writable**. `data-pkg/post-install.xql` sets this (`rwxrwxr-x` on collections, `rw-rw-r--` on files) for `workspace`, `registers`, `places`, `people`, etc. If a save returns **500 "Write permission is not granted on the Collection"** — or in-place register edits fail — the deployed permissions have drifted (commonly: files re-stored by `admin` via REST PUT). Fix by re-running the `post-install.xql` chown/chgrp/chmod block as admin. Register files specifically need **`tei` ownership** (eXist takes a collection-wide write lock for in-place updates), so after deploying a register XML via admin PUT, restore `tei` ownership.

**Persons store:** `registers/persons.xml` (`pb-persons`) is the single read source — list, detail, chronology, and editor person-picker (`/api/editor/people`). The legacy `data/people/*.xml` per-file store is retained only for the editor person-entity CRUD route (`/api/editor/people/{id}`).

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
