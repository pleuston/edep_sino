# Upstream tracking

This app is based on **eeditiones/edep**, branch **`edep-jinks`** (the TEI Publisher 10 / Jinks port).
Remote: `upstream` = https://github.com/eeditiones/edep.git

| What | Ref |
|---|---|
| Base of `sino-tp10` | `upstream/edep-jinks` @ `87f53c7` (2026-05-18, "feat(config): update jinks configuration") |
| Editor porting source | `upstream/altered-model` @ `6fc26d8` (2026-05-28) — tagged `editor-port-src` |

## Sync policy

`git fetch upstream && git merge upstream/edep-jinks` into `sino-tp10` — merge, never rebase (published branch). After each sync, record date/commit/conflicts below. Re-check both upstream branch heads before starting any new milestone: upstream is actively porting EDEp to TP10 and may land their own editor port.

## Sync log

| Date | Merged | Conflicts / notes |
|---|---|---|
| 2026-06-11 | branch created from `87f53c7` | — |

## Divergence inventory (ours vs upstream/edep-jinks)

- **Identity rename** `edep-jinks` → `edep-sino`, data app `edep-data` → `edep-sino-data` (M0). Touches: `.existdb.json`, `build.xml`, `config.json`, `context.json`, `cypress.config.cjs`, `expath-pkg.xml`, `modules/custom-api.json`, `modules/lib/api.json`, `modules/registers-api.json`, `package.json`, `repo.xml`, `README.md`, ODDs (`output.odd`, `edep.odd`, `edep-output.odd`, `edep-edition.odd`), `modules/generated-config.xql`, `modules/odd-global.xqm`, `doc/zotero-cache.md`. These files will conflict trivially on every upstream sync — resolve by re-applying the rename.
- **`data-pkg/` data package** (M1, new directory — no upstream counterpart in this repo). Upstream's edep-data (gitlab akademie-mainz, master branch) still has the old flat layout; the jinks-era layout (`data/taxonomy/*.xml`, `data/registers/`, `data/landing/landing.xml`) was reconstructed from the app's expectations (fx-instance srcs on `altered-model`, `config:get-document`, register-map). Taxonomy files are TEI `<taxonomy>` docs with `category/@corresp` + multilingual `catDesc` (placeholder content until M5; URI scheme `sino:` finalized in M4).
- **Landing content lives in the data package** (M1): `view.xql` resolves the landing profile's `data.landing = landing/landing.xml` against `$config:data-root`, so `data-pkg/data/landing/landing.xml` (copy of the app's `data/landing/landing.xml`) is required or `index.html` 500s with `$landing is not set`. Candidate upstream doc fix.
- **Test adjustments** (M1, candidates to upstream):
  - `test/cypress/e2e/api/authentication.cy.js` "handles missing credentials": roaster 1.12 answers `200` + guest session for a credential-less login (session fallback) — assertion now accepts 200-without-identity or 401.
  - `test/cypress/e2e/gui/landing-page.cy.js`: URL assertion tolerates the `?lang=` query appended by `language.js`; explore-link test no longer assumes a "highlights" page (EDEp's landing links to browse).
  - `test/cypress/e2e/gui/metadata-panel.cy.js`: `describe.skip` + TODO(M7) — the generated suite visits the TEI Publisher demo Kant document with `dta.odd`, which EDEp does not ship.
- (grows per milestone)

## Coordination issue (draft — to be sent by the maintainer)

*To be drafted in M9: announce the editor port (altered-model parts → jinks structure, namespaced `templates/parts/edit/` + `/api/editor/*` routes) and the Chinese-epigraphy layer, offer the generic parts upstream, ask about upstream's editor-port timeline to avoid duplicate work.*
