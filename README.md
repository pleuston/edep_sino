# EpiWen 中文石刻數位編輯工具

**Editing tools for Chinese digital epigraphy**, built on [TEI Publisher 10](https://teipublisher.com/) and descended from [eeditiones/edep](https://github.com/eeditiones/edep). The application catalogues and edits Chinese inscriptions (碑/碣/摩崖/造像記/經幢/墓誌…) as EpiDoc TEI — the editing form operates directly on the XML in the browser, no mapping layer in between.

## What it does

- **Inscription editor** ([Fore](https://jinntec.github.io/Fore/doc/index.html)-based): object description, production roles (撰文/書丹/刻/題額/立石), find spot with geo-picker, witnesses — rubbings 拓本 as first-class text carriers with their own descriptions, layout (行數/滿行/writing direction), script styles (篆隸八分楷行草魏碑), dual Leiden+/EpiDoc transcription editor with one-click markup for 誤字, 通假, 避諱, 異體字, 闕字, 抬頭, 缺/漫漶.
- **Chinese dating**: type the date as carved (永和九年歲在癸丑), pick era + reign year + 干支, and the converter — backed by the DDBC Time Authority (927 era names, 5118 reign years) — writes exact proleptic-Gregorian ISO ranges with a cyclical-year consistency check. Era names repeated across dynasties are disambiguated, never silently resolved.
- **Reading view**: editions in Literary Chinese render in vertical right-to-left columns (toggleable), variant glyphs reveal their standardized mapping in a popover.
- **Registers**: persons with 字/號/諡號/廟號 and offices; places with period-resolved historical names, administrative hierarchy and WGS84 coordinates (CHGIS/TGAZ links).
- **Trilingual interface**: English, Deutsch, 繁體中文.

Every encoding decision is specified in **[doc/sino-model.md](doc/sino-model.md)** — the contract derived from the Epiwen element-by-element EpiDoc analysis of Chinese epigraphy. Stored documents validate against `tei-epidoc.rng` plus two documented sino extensions (`scripts/validate-epidoc.sh`).

## Quick start

```sh
docker run -dit -p 8080:8080 --name epiwen-db existdb/existdb:6.4.0
npm install && ant xar-local          # application xar
(cd data-pkg && ant)                  # data package xar
# install: roaster, jinks-templates, tei-publisher-lib 6, data package, app
# (exact commands: doc/INSTALL.md)
open http://localhost:8080/exist/apps/epiwen/
```

Login `tei` / `simple`. A fictional specimen inscription (`demo-zaoxiangji` 測試造像記) demonstrates every field.

## Documentation

| | |
|---|---|
| [doc/INSTALL.md](doc/INSTALL.md) | verified local bring-up |
| [doc/ARCHITECTURE.md](doc/ARCHITECTURE.md) | how app, data package, editor, registers and ODDs fit together |
| [doc/DEVELOPMENT.md](doc/DEVELOPMENT.md) | build system, templating, how to add fields/vocabularies/routes |
| [doc/sino-model.md](doc/sino-model.md) | the Chinese EpiDoc encoding manual (the contract) |
| [doc/USER-GUIDE.md](doc/USER-GUIDE.md) | editor walkthrough for epigraphers |
| [doc/UPSTREAM.md](doc/UPSTREAM.md) | relationship to eeditiones/edep (`edep-jinks`), sync log, divergences |
| [doc/DEPLOYMENT.md](doc/DEPLOYMENT.md) | production packaging |

## Stack & provenance

TEI Publisher 10 (Jinks app structure, tei-publisher-lib 6, jinks-templates, roaster) on eXist-db ≥ 6.2 · pb-components 3 · Fore 3 · jinn-codemirror. Based on the `edep-jinks` branch of eeditiones/edep with the modernized editor ported from `altered-model`; all divergences are logged for re-upstreaming. Tests: `npx cypress run` (130+ specs).

## Licenses

GPLv3. `data-pkg/data/taxonomy/nianhao.xml` is derived from the [DDBC Time Authority](https://authority.dila.edu.tw/) and licensed CC BY-SA 3.0.
