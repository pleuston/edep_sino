# EDEp Sino — User guide for epigraphers

*State: M7 — covers the editor for Chinese inscriptions. Registers and the Chinese interface follow in later milestones.*

EDEp Sino catalogues Chinese inscriptions as EpiDoc TEI. You never see the XML unless you want to: the editing form reads and writes the document directly. The encoding conventions behind every field are specified in `doc/sino-model.md`.

## Opening the editor

- New inscription: `…/edep-sino/edit.html` (log in first — default user `tei`).
- Existing inscription: open it from *Browse* or `…/edit.html?id=<EDEp-id>&collection=workspace`.
- The left navigation jumps to the form sections. **Save** sits in the bar at the bottom; the first save assigns the EDEp identifier.
- A worked example ships with the app: the fictional specimen `demo-zaoxiangji` (測試造像記) exercises every field of this guide.

## The sections

**Identifier** — repository, inventory numbers. The EDEp id is assigned automatically.

**Production (撰書刻)** — who composed (撰文), wrote (書丹), carved (刻), titled (題額) and erected (立石) the inscription. Add one row per role; record unknown agents as 未詳 rather than omitting the role. These are *production* roles — the modern editor of the record is captured under *Editing*, never here.

**Finding / Present location** — find spot via the place picker (places carry WGS84 coordinates; mainland-published coordinates are GCJ-02-shifted — convert before entering), provenance events, current repository.

**Witnesses (拓本)** — rubbings and transmitted copies are *witnesses with their own description*, not images of the stone: type (拓本 rubbing / 原石 stone autopsy / 録文 transmitted), siglum, holding institution, shelfmark, date of taking, taker (拓工), condition. Photographs of the stone itself belong under *Images*, not here.

**Description of object** — object form (碑/碣/摩崖/造像/經幢/墓誌…), material, decoration (螭首, 龜趺, 額, 界格…), measurements (cm; keep the source 尺/寸 statement in the text field).

**Inscription field** — the inscribed zone: height/width, **columns 行數**, **characters per full column 滿行**, **writing direction** (vertical right-to-left for most carved texts), character heights (字徑) per zone.

**Description of text** — languages of the text (Literary Chinese `lzh` is the default carved language), metre (prose / 四言 / 五言 / 七言…), **script style** (篆/隸/八分/楷/行/草/魏碑 — 榜書 is a size class, not a script).

**Chronological data** — the Chinese dating workflow:
1. Type the **literal date** exactly as carved: 太和廿二年九月十四日.
2. Enter era name (年號 — autocompleted), reign year, and the cyclical year (干支) if the text gives one.
3. **Convert**: all dynasties using that era name appear with exact proleptic-Gregorian ranges. A 干支 mismatch is flagged (應為…) — that is research data, not an error to silence.
4. **Apply** the right candidate: the ISO values (`when`, `notBefore`, `notAfter` — the true lunisolar span over two western years), the era-year token (太和二十二年), the dynasty facet and the machine-readable native value are written into the record. All remain hand-editable.

**Edition** — transcription in the dual editor (Leiden+ / EpiDoc XML). One `<lb n="…"/>` per column 行, numbered in carving order (rightmost = 1). Toolbar buttons cover the sino phenomena:

| Button | Phenomenon | Markup |
|---|---|---|
| 誤字 | carver's error | `<choice><sic>戊</sic><corr>戌</corr></choice>` |
| 通假 | phonetic loan | `<choice ana="#jiajie"><orig>區</orig><reg>軀</reg></choice>` |
| 避諱 | taboo substitution | `<choice ana="#bihui">…</choice>` |
| 異體 | variant/missing glyph | `<g ref="#g-…">為</g>` + glyph record |
| 闕字 | honorific blank | `<space … subtype="que-zi"/>` |
| 抬頭 | raised head | `<lb n="…" rend="taitou-ping"/>` |
| 缺 | lost characters | `<gap reason="lost" quantity="…" unit="character"/>` |
| 漫漶 | illegible characters | `<gap reason="illegible" …/>` |

Counting unit is always the **character**. Whitespace inside the edition is preserved (it carries meaning — 闕字).

**Apparatus / Translation / Commentary** — one translation block per language; text-critical argument goes to the apparatus, exegesis to the commentary.

**Historic relevance / Editing** — subject keywords (religion etc.) and the modern editorial responsibility + publication status.

## Validation

Saved documents conform to EpiDoc (tei-epidoc.rng) plus two documented sino extensions (witness lists; glyph records) — checked with:

```sh
npm run validate:demo            # or: scripts/validate-epidoc.sh <file.xml>
```
