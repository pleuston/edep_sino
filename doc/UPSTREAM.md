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
- (grows per milestone)

## Coordination issue (draft — to be sent by the maintainer)

*To be drafted in M9: announce the editor port (altered-model parts → jinks structure, namespaced `templates/parts/edit/` + `/api/editor/*` routes) and the Chinese-epigraphy layer, offer the generic parts upstream, ask about upstream's editor-port timeline to avoid duplicate work.*
