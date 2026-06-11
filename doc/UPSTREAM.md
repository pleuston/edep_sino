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
- **Editor port** (M2): `templates/edit.html` + `templates/parts/edit/*` + `templates/fore/*` + `templates/geo-picker.html` ported from `upstream/altered-model` (tag `editor-port-src`) into the jinks structure. Conversions: eXist html-templating idioms → jinks-templates (`lib:include` → `[% include %]`, `${app}` → `[[ $context-path ]]`, `pages:parse-params` → `page:parameter`), Polymer shell dropped, `iron-icon` → own `<edep-icon>` component (`resources/scripts/edep-icons.js`), data refs → `edep-sino-data`. New `resources/css/edit.css` reconciles the editor with the jinks grid + pico. Fore bumped to ^3.1.2, `@jinntec/jinn-codemirror` 1.19.0 added (bundle + tei.json copied by `ant xar-local`).
- **Editor API port** (M3): `modules/custom-api.{json,xql}` now carry the inscription editor API from `altered-model` (inscription GET/POST, fragment, render, epidoc download via new `eapi:epidoc`, places/people entity routes, geopicker, zotero); `modules/lib/api/zotero.xql` ported; `modules/lib/api.xql` imports them (prefix `eapi`) and routes `modules/custom-api.json` first. Collisions with the registers profile resolved by renaming the entity browse routes to `GET /api/editor/places|people`. `resources/odd/edep-clean.odd` registered as internal ODD (`generated-config.xql`) — the save pipeline's cleanup transform. Editor config block (places/people/inscription/zotero vars) appended to `modules/config.xqm`. Classic pretty routes (`/edit/{collection}/…`, `/orte`, `/personen`) intentionally not ported — the editor uses `/edit.html?collection=…&id=…` and `updateUrl()` now sets the `id` query parameter (s-create also syncs `params/id` + URL, which classic did not).
- **Sino vocabularies + data v1** (M5): all taxonomy files now carry real Chinese content per `doc/sino-model.md` (object forms, genres, materials, closed script list, decoration, condition terms, dynasty periodisation with machine ranges in `@n`, production roles, languages, metre, religion). Register seeds in both storage models: entity files (`data/people/*.xml`, `data/places/*.xml` — what `registers-api.xql` browses and the geo-picker loads) and standOff register docs (`data/registers/*.xml` — entry templates/bibliography). **Route shadowing fix**: roaster resolves a path in the first spec that declares it, so a POST-only `/api/people` in custom-api.json had 405'd the registers' GET — all editor entity routes now live under `/api/editor/*` (geo-picker updated).
- **Chinese dating** (M6): `modules/sino/dates.xqm` + `GET /api/sino/era|eras` (nianhao lookup with exact lunisolar reign-year spans, proleptic Gregorian, ganzhi check, dynasty→period CURIE mapping); `data-pkg/data/taxonomy/nianhao.xml` generated from the DDBC Time Authority (927 eras / 5118 reign years, CC BY-SA 3.0); `templates/parts/edit/dating.html` rewritten per `doc/sino-model.md` §1 (literal era string = origDate content — replaces classic EDEp's prose-remarks use of that slot); template origDate gains `@when/@notBefore/@notAfter/@n/@period` (Julian-calendar default dropped); `edep-clean.odd` origDate model reduced to copy — empty-attribute stripping moved to `api:postprocess` so the extended attribute set survives saving.
- **Sino object/text fields** (M7): template gains layout `@columns/@writtenLines/@style`, origDate sino attribute set, `listWit`, `charDecl`, `lzh` language defaults, edition `@xml:lang`+`@xml:space`; new parts `witnesses.html` (rubbings as first-class witnesses) and `production.html` (typed 撰書刻 respStmt roles, selector guard added to `verification.html`'s template origin); sino transcription snippets in the edition XML toolbar; `api:postprocess` guards (origDate empty-attribute strip; type-less empty idno strip — UI node-creation against incomplete imports). Validation gate `scripts/validate-epidoc.sh` (vendored `test/schema/tei-epidoc.rng` + documented sino-extension allowlist); demo inscription `data-pkg/data/workspace/demo-zaoxiangji.xml` (fictional specimen) exercises every field and validates, including after a UI save. Schema findings logged in `doc/sino-model.md` "Schema-conformance adjustments" (choice/@type→@ana; EpiDoc prunes listWit/glyphName/char; classic empty placeholders `resp/@when`, empty `facsimile`, `term/@ref=""` are EpiDoc-invalid — upstream FYI).
- (grows per milestone)

## Coordination issue (draft — to be sent by the maintainer)

*To be drafted in M9: announce the editor port (altered-model parts → jinks structure, namespaced `templates/parts/edit/` + `/api/editor/*` routes) and the Chinese-epigraphy layer, offer the generic parts upstream, ask about upstream's editor-port timeline to avoid duplicate work.*
