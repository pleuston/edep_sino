# EDEp Sino — Chinese EpiDoc encoding manual

*The contract for all Chinese-epigraphy fields (milestones M5–M9). Derived from the **Epiwen** element-by-element EpiDoc/TEI analysis (recalled 2026-06-11) and crosswalked against the EDEp data model. Each decision carries a confidence label:*
**[Epiwen]** = attested decision in the Epiwen walk · **[fill]** = Epiwen silent, best-practice fill · **[divergence]** = Epiwen and EDEp disagree; the v1 resolution is recorded here and is the binding one for this app. *Review this file asynchronously — changing a decision here means re-touching the implementing files listed with it.*

## Frame

Epiwen models an edition as **one inscribed text (E-TXT) on one support (E-SUP), produced by a role-typed event (E-PRD), reconstructed from witnesses (E-WIT: 原石 stone / 拓本 rubbing / 録文 transcription)**. Four non-negotiables that constrain everything below:

1. calligrapher ≠ author (production roles are typed, never `<author>`),
2. a rubbing is a first-class witness, never a surrogate,
3. text ≠ support,
4. production is a role-typed event.

---

## 1. Dating 年號 · 干支 **[Epiwen, with one documented repurpose]**

```xml
<origDate calendar="#reign-tang #ganzhi" period="sino:dynasty:tang"
          when="0726" n="開元十四年"
          when-custom="kaiyuan:14" datingMethod="#gregorian-converted"
          evidence="internal">開元十四年丙寅</origDate>
```

- **Literal era string = element content**, preserved verbatim (永和九年歲在癸丑). Never normalised. **[Epiwen]**
- **`@n`** = the literal era-year token, queryable un-converted. **[Epiwen]**
- **`@when/@notBefore/@notAfter`** = derived **proleptic-Gregorian** ISO values (4-digit years). Dynasty-only dating = a range from the dynasty authority + `@cert`, never a fake point. **[Epiwen]** — note: printed sinological concordances are Julian-based before 1582; the conversion service (M6) documents its handling.
- **`@when-custom`** = machine-sortable native value `{era-id}:{reign-year}` (e.g. `kaiyuan:14`). Epiwen defers `-custom` to v1.x "if a tool needs it" — **EDEp is that tool** (the form needs a parseable slot to repopulate era/year fields). **[divergence #1 resolved: dual encoding]** The form binds the plain family for ISO values *and* the `-custom` slot for the native value; `checkDate` validation moves to the plain attributes.
- **`@calendar`** multi-valued, pointing at `<calendarDesc>` calendars (`#reign-…`, `#ganzhi`); **`@datingMethod`** names the conversion rule. **[Epiwen]**
- **`@period`** → dynasty taxonomy (browse facet). **[Epiwen]**
- 干支 cross-check: era year vs cyclical year; mismatch → `@cert` + both recorded. **[Epiwen]**

**Implements:** `templates/parts/edit/dating-sino.html` + `modules/sino/dates.xqm` + `/api/sino/era` (M6) · `data-pkg/data/taxonomy/dynasty.xml` (periodisation, M5) + `nianhao.xml` (era table with ISO ranges = the conversion authority, M6) · template `origDate` attributes (M7).

## 2. Layout & writing direction **[Epiwen core; direction attr = fill]**

- `<lb/>` = the physical column 行, `@n` = column number **in carving order (rightmost = 1)**; `<cb/>` is *never* used for 行. **[Epiwen]**
- One `<layout>` per support zone; 行數 = `@columns`; 滿行 (chars per full column) = `@writtenLines` reinterpreted + prose count in content. Direction: TEI has no native attribute → carried by `@style="writing-mode: vertical-rl"` on `<layout>` and a `<rendition xml:id="rtl-vertical">` in `tagsDecl` for display. **[fill — Epiwen's `@writingMode` example is not schema-valid; settled part is "one layout per zone, 行數 + 滿行 + explicit direction"]**

```xml
<layout n="碑陽" columns="22" writtenLines="51" style="writing-mode: vertical-rl">
    <p>正書，二十二行，滿行五十一字。</p>
</layout>
```

- `xml:space="preserve"` mandatory on `<div type="edition">`; whitespace is meaningful (闕字). **[Epiwen]**
- 闕字 honorific blank = `<space dim="vertical" quantity="1" unit="character" subtype="que-zi"/>`; 抬頭 raised head = `@rend="taitou-ping|taitou-dan|taitou-shuang"` on the opening `<lb/>`. **[Epiwen, open fork #5]**
- Rendition ladder: script→`@hand` · size→`@rend` (`bangshu|large|small|normal`) · layout devices→`@rend` on `<lb>`/`<space>` · appearance→`@rendition` set in `tagsDecl`. **[Epiwen]**
- Edition language: `xml:lang="lzh"` (Literary Chinese), **not** `zh-Hant` (script tag). **[Epiwen]**

**Implements:** layout form fields in `templates/parts/edit/inscription-field.html`/`text-description.html` (M7) · template `layoutDesc` + edition div attrs (M7) · `tagsDecl` rendition set in the ODD + vertical preview CSS (M9).

## 3. Script styles on handNote **[Epiwen content; binding = EDEp house style]**

- One `<handNote>` per hand/zone, `@xml:id`-keyed; `@scope` for the zone (額/碑陽).
- Script values from a **closed custom taxonomy** (not ISO 15924): 篆 `zhuan` · 隸 `li` · 八分 `bafen` · 楷 `kai` · 行 `xing` · 草 `cao` · 魏碑 `weibei`; **榜書 is a size class, not a script** → `@subtype="bangshu"`. Contested boundaries recorded with parent class + `@cert`. **[Epiwen]**
- Calligrapher co-reference: `@scribe="#person"`; model attribution (法二王) = `<persName role="model" cert>` inside the note. **[Epiwen]**
- **[divergence #2 resolved]**: canonical Epiwen home is `profileDesc/handNotes`; EDEp edits `physDesc/handDesc/handNote` — **keep `handDesc` as the single home** (tooling), adopt Epiwen content conventions. Binding via `@corresp="sino:script:…"` (EDEp house pattern); the ODD may additionally fix `@script` tokens. **[divergence #7 resolved likewise]**

**Implements:** `data-pkg/data/taxonomy/paleography.xml` extension (M5) · `templates/parts/edit/text-description.html` handNote fields (M7).

## 4. Variant 異體字 & taboo 避諱 characters **[Epiwen routing table]**

| Phenomenon | Markup |
|---|---|
| 誤字 carver error | `<choice><sic>戊</sic><corr>戌</corr></choice>` |
| 通假字 phonetic loan | `<choice ana="#jiajie"><orig>蚤</orig><reg>早</reg></choice>` |
| 合文 ligature | `<choice><abbr>廿</abbr><expan><ex>二十</ex></expan></choice>` |
| 重文 ditto 〻 | `子<choice><abbr><g ref="#chong-wen"/></abbr><expan>子</expan></choice>` |
| **異體字/缺字** | **`<g ref>` + `<charDecl>`** — glyph identity, *never* `orig/reg` |

- Variant **with** Unicode codepoint (incl. Ext B–G): encode the carved codepoint directly. **[Epiwen]**
- Variant **without** codepoint: `<g ref="#g-…"/>` + `<glyph>` with `<glyphName>`, **IDS decomposition**, `<mapping type="standardized">` + GlyphWiki/CHISE mappings. 缺字 = `<char>` with IDS `<charProp>`. **[Epiwen]**
- Taboo: ground-out → `<del rend="erasure"><gap…/></del>` + note · recut 諱改 → `<subst>` · in witness → `<rdg cause="transmission">` · as dating evidence → `@evidence="bihui"` on origDate. **[Epiwen]** In-carving avoidance (缺筆 stroke omission → `<g>`+glyph with taboo note; substituted homophone → `<choice ana="#bihui"><orig/><reg/></choice>`). **[fill]**
- 繁/簡 is an `xml:lang` register distinction, never `<choice>`. **[Epiwen]**

**Implements:** jinn-codemirror toolbar snippets for the routing table (M7) · `charDecl` slot in template `encodingDesc` (M7) · shared glyph register `data-pkg/data/registers/glyphs.xml` (deferred to v1.x — open fork #1; v1 uses per-file charDecl).

## 5. Rubbings 拓本 **[Epiwen — "the sharpest line in the model"]**

- A rubbing is **NEVER** `bibl @type='rubbing'`, never a `<facsimile>` of the stone, never a surrogate. It is a **first-class `<witness type="rubbing">`** in `sourceDesc/listWit` with its own `msDesc` (repository + idno, date of taking + `<persName role="taker">`, paper/ink/condition). Witness types: `autopsy` (stone) · `rubbing` · `transmitted` (録文 → `listBibl` detail). **[Epiwen]**
- `<surrogates>` = photographs/scans/IIIF **of the stone** only. **[Epiwen]**
- Facsimile binding: one `<surface>` per witness image, `@corresp` to the witness; `surface/@type` ∈ `photo-original|rubbing-scan|historical-reproduction`. **[Epiwen]**
- **[divergence #4 resolved]**: v1 adds a minimal `<listWit>` block + a skeleton rubbing form (repository, idno, dating, condition); existing `listBibl[@type='transmission']` continues to host 録文 references; apparatus `@wit` keying grows in v1.x.

**Implements:** template `listWit` slot + `templates/parts/edit/witnesses.html` (new part, M7) · `templates/parts/edit/pictures.html` surface @type (M7).

## 6. Person names **[Epiwen]**

In-text: whole names + `@ref` (no forced decomposition; 複姓 kept whole); `<addName @type>` closed list `zi 字 · hao 號 · dharma 法號 · posthumous 諡 · temple-name 廟號 · fief 封號`; `<genName type="hangdi">` 行第; **`<roleName>` = office in life** (`office|clerical|rank|fief|exam`) — rigorously distinct from `persName/@role` = **production role on this monument** (`composer 撰文 · calligrapher 書丹 · carver 刻 · titler 題額 · erector 立石`).

Register (standOff): canonical `<persName type="canonical">` (emperor→廟號, monk→法號) + optional segmented personal name; **`<listNym>`/`<nym @type>`** mirrors the name system; `<persState type="office">`; `<floruit>` defaulted to production date; `@sameAs` → CBDB id. Production roles never sit on `<person>`.

**Implements:** `data-pkg/data/registers/persons.xml` entry shape + register form templates (M8) · `data-pkg/data/taxonomy/roles.xml` production roles, kept separate from `editor-roles.xml` (M5) · `respStmt @resp` typed entries in template `titleStmt` (M7).

## 7. Places **[Epiwen]**

- In-text tiers all `@type`d and period-resolved: `<region type="dao|lu|xingsheng|sheng">`, `<settlement type="zhou|xian|fu|jun|cun">`, `<district type="xiang|li|fang">`; natural features (摩崖 site!) = `<geogName>`/`<geogFeat type="mountain|peak|cliff|…">`.
- Register `<place>`: `@type="feature|settlement|region|administrative"`; **multiple `<placeName>` with `@notBefore/@notAfter`** (period-resolved names); `<location><geo>` decimal **WGS84** — PRC published coordinates are GCJ-02-offset: convert and record source datum (`<geoDecl datum="WGS84">`); nested region/settlement with period bounds; `@sameAs="tgaz:…"` (CHGIS/TGAZ = authority of record; prefixes via `<listPrefixDef>`). DILA prefix for monasteries **[fill]**.

**Implements:** `data-pkg/data/registers/places.xml` entry shape + register forms + geo-picker WGS84/GCJ-02 note (M8) · `taxonomy/province.xml`/`country.xml` stay the *modern* location vocabulary.

## 8. Object / material / decoration vocabularies **[Epiwen categories; URIs = open fork #7]**

- **Object forms** (`objtyp.xml`): 碑 bei · 碣 jie · 摩崖 moya · 造像記 zaoxiangji · 經幢 jingchuang · 墓誌 muzhi · 石柱 shizhu · 畫像石 huaxiangshi · 塔銘 taming. Form ≠ genre.
- **Genres** (`typeins.xml`): 封禪 · 題名 · 題刻 · 造像記 · 經幢 · 墓誌銘 · 刻經 · 詩刻 · 碑頌 · 法帖.
- **Materials** (`material.xml`): 花崗岩 granite · 石灰岩 limestone · 砂岩 sandstone · 大理石 marble · 玉 jade + living rock (moya); open extension → bronze 青銅, brick 磚 retained **[fill]**. AAT crosswalk glosses where verified.
- **Decoration** (`decor.xml`): 螭首 chishou · 龜趺 guifu · 碑座 beizuo · 額 e · border; one `<decoNote @type>` per feature; the 額 dual-codes as deco + text zone. **[divergence #5 resolved]**: 界格 stays in `decor.xml` for v1 with a documented broadened scope (Epiwen reads it as a layout fact).
- `<objectType @ref>` is the canonical token home; vocabularies = TEI `<taxonomy>` of `<category @corresp>` with trilingual `<catDesc>` (zh + en + de here; pinyin in `@xml:id`s). **URI scheme**: CURIEs `sino:{vocab}:{id}`, declared in `<listPrefixDef>` with base `https://pleuston.github.io/edep_sino/voc/` — **placeholder; open fork #7**, changeable in one place.

**Implements:** all vocabulary files in `data-pkg/data/taxonomy/` (M5) · `listPrefixDef` in template (M7).

## 9. Further essentials

- **Production roles** (the load-bearing rule): `titleStmt/respStmt/resp @type` ∈ 撰文/書丹/刻/題額/立石; unfilled roles recorded as 未詳; contested `@cert="low"`; `<author>/<editor>` reserved for the modern edition. New `taxonomy/roles.xml`. (M5/M7)
- **Translation**: one `div[@type='translation']` **per language** with mandatory `@xml:lang` + `@corresp` alignment. (M7)
- **Apparatus**: `app/@type` ∈ `variant-readings|alternative-restoration`; `rdg/@cause` ∈ `weathering|breakage|recutting|transmission|rubbing-artefact`; double-end-point external in `div[@type='apparatus']`. (v1 keeps the div; @wit keying grows with listWit.)
- **Measurements**: `@quantity @unit="cm"` + verbatim 尺/寸 in content; typed dimensions incl. **charHeight 字徑** (headline datum) and `field` (inscription field, no depth on moya). (M7)
- **Condition** (`preservation.xml`): 漫漶 · 殘缺 · 佚失 · 磨改 · 覆刻 — weathering vs intentional kept distinct. (M5)
- **Text structure**: `div[@type='textpart'] @subtype` ∈ `xu 序|ming 銘|zhi 誌|kuanzhi 款識|timing 題名|juanzi 捐資`; verse = `<lg type="ming|ji-gatha|shi" subtype="siyan|wuyan|qiyan">` with `<lb/>` milestones; name registers = `<list type="timing|juanzi|zhiguan-timing">`; 款識 = `<closer>/<dateline>/<signed @role>`. (M7 snippets; full forms v1.x)
- **Damage discipline**: `@unit="character"`; `<gap reason="lost|illegible">` by reading-offered test; `<supplied @source>`; `<damage @agent>`. (M7 codemirror snippets)
- **Identifiers** **[divergence #3 tolerated v1]**: EDEp keeps `idno @type="EDEp"` in `msIdentifier`; correct three-home split (edition/stone/rubbing) + shared **support register** for one-support-many-texts deferred (v1.x; `relatedItem @type="same-support|recutting-of|parallel"` documented now).
- **Fragments** **[divergence #6 tolerated v1]**: EDEp's separate-doc mechanism (`TEI/@fragments` + `@corresp/@type='partial'`) kept; Epiwen's `<msFrag>`/`<locusGrp>` crosswalk documented, not merged.
- **Languages**: template default `lzh`; editorial `zh-Hant/zh-Hans/en/de`; romanisation `zh-Latn-pinyin`; 五體碑 multilingual = separate parallel editions. `languages.xml` extended. (M5/M7)
- **Provenance**: `@type` list extended `found(≈excavation)|re-erection|burial|excavation|relocation|history`. (M7)
- **Religious affiliation**: subject keywords (`religion.xml`) — not an Epiwen category **[fill]**; attested Buddhist specifics: 邑義 donor society = `orgName @type="donor-society"`, sutra quotes = `<quote source="cbeta:…">`.

## Schema-conformance adjustments (v1, found by the tei-epidoc.rng gate)

- **`choice/@type` → `choice/@ana`** (`#jiajie`, `#bihui`): the EpiDoc schema does not admit `@type` on `choice`; `@ana` is valid and semantically the analysis pointer. Deviates in letter, not intent, from the Epiwen snippet.
- **`listWit` in `sourceDesc` is NOT in the EpiDoc schema** — kept regardless (contract par.5 is non-negotiable) and carried as a sanctioned extension in the validation gate (`scripts/validate-epidoc.sh` allowlist) until the sino ODD/RNG exists (open fork).
- **Gaiji pruning**: EpiDoc keeps `glyph` + `mapping` but prunes `glyphName`/`charProp`/`char` — IDS decompositions for 缺字 are deferred to the sino ODD (open fork #1); v1 glyph records use `mapping` (+ prose `desc`).
- Classic EDEp placeholders that are schema-invalid when empty (`resp/@when`, empty `facsimile`, `term/@ref=""`) are stripped by the save cleanup; the upstream template still carries them (logged in doc/UPSTREAM.md).

## Open Epiwen forks (not silently resolved here)

(1) glyph bank scale/registry mechanics · (4) 書丹-vs-刻 one event or two (v1: one creation, multiple typed agents) · (5) 抬頭 `@rend`-on-`<lb>` extension · (6) TEI↔IIIF binding · (7) final CURIE base URIs · (8) 撰 never as `<author>` (walk says never) · TP rendering of external double-end-point apparatus.

## Milestone map

| Milestone | Implements from this contract |
|---|---|
| M5 | All vocabulary files (§1 dynasty, §3 paleography, §8 objtyp/typeins/material/decor, §9 roles/preservation/languages) |
| M6 | Dating service + form (§1), nianhao.xml authority |
| M7 | Template extensions (origDate attrs, layout, handNote, listWit, charDecl, dimensions, respStmt, textpart/damage snippets, lzh defaults, listPrefixDef), editor parts, roundtrip fixture |
| M8 | Registers: person entry shape + nym system, place entry shape + period names + WGS84 (§6–7) |
| M9 | Rendition set + vertical preview, variant-char display, zh UI |
