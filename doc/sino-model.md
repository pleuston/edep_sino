# EpiWen — Chinese EpiDoc encoding manual

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
- `<objectType @ref>` is the canonical token home; vocabularies = TEI `<taxonomy>` of `<category @corresp>` with trilingual `<catDesc>` (zh + en + de here; pinyin in `@xml:id`s). **URI scheme**: CURIEs `sino:{vocab}:{id}`, declared in `<listPrefixDef>` with base `https://pleuston.github.io/epiwen/voc/` — **placeholder; open fork #7**, changeable in one place.

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

## 8bis. Visual form & seals (medium beyond carved stone) **[fill — DRECE design]**

EDEp's corpus is carved stone, but the DRECE design and the NPM examples (法書 calligraphy, 經塔 with 朱書 + 繪畫 + 鑑藏印) require recording other visual/material forms on the same object model.

- **Visual form** = `objectDesc/@form` keyed into a new `medium` taxonomy: 刻石 carved stone · 法書 calligraphy · 墨跡 ink on paper/silk · 繪畫 painting · 鈐印 seal impression · 拓本 rubbing-as-object · 寫本 manuscript · 刻本 woodblock print. EpiDoc-valid (`@form` is free on `objectDesc`); empty placeholder stripped on save (`api:postprocess`). Editor: a select in `objectdesc.html`.
- **Seals 鈐印** = `physDesc/sealDesc/seal`, each `seal/@type` (new `sealtype` taxonomy: 鑑藏印 collector · 名章 name · 齋館印 studio · 引首印 leading · 閒章 leisure), `seal/p` for the legend 印文, optional `@corresp` → person register for the seal's owner. EpiDoc-valid **only with non-empty `@corresp`** — the empty placeholder is dropped in `api:postprocess` (`seal` case) and empty `sealDesc`/`seal` are omitted by `edep-clean.odd`. Editor: repeatable seal rows in `objectdesc.html`.
- Deferred: a shared **seals register** (a collector's 鑑藏印 reused across objects, like persons/places) — `@corresp` already points at the person register for owners; a dedicated seal authority is v1.x. Metadata-display ODD rendering of `@form`/`sealDesc` (the inscription view) is also a follow-on; the editor + stored XML are complete.

## Schema-conformance adjustments (v1, found by the tei-epidoc.rng gate)

- **`choice/@type` → `choice/@ana`** (`#jiajie`, `#bihui`): the EpiDoc schema does not admit `@type` on `choice`; `@ana` is valid and semantically the analysis pointer. Deviates in letter, not intent, from the Epiwen snippet.
- **`listWit` in `sourceDesc` is NOT in the EpiDoc schema** — kept regardless (contract par.5 is non-negotiable) and carried as a sanctioned extension in the validation gate (`scripts/validate-epidoc.sh` allowlist) until the sino ODD/RNG exists (open fork).
- **Gaiji pruning**: EpiDoc keeps `glyph` + `mapping` but prunes `glyphName`/`charProp`/`char` — IDS decompositions for 缺字 are deferred to the sino ODD (open fork #1); v1 glyph records use `mapping` (+ prose `desc`).
- Classic EDEp placeholders that are schema-invalid when empty (`resp/@when`, empty `facsimile`, `term/@ref=""`) are stripped by the save cleanup; the upstream template still carries them (logged in doc/UPSTREAM.md).

## Open Epiwen forks (not silently resolved here)

(1) glyph bank scale/registry mechanics · (4) 書丹-vs-刻 one event or two (v1: one creation, multiple typed agents) · (5) 抬頭 `@rend`-on-`<lb>` extension · (6) TEI↔IIIF binding · (7) final CURIE base URIs · (8) 撰 never as `<author>` (walk says never) · TP rendering of external double-end-point apparatus.

## §10 Jinshi history layer — Works, Inscription authority, Timelines (M-J1–M-J5)

This section extends the model to cover the *historiography* of Chinese epigraphy (金石學): the scholarly tradition of compiling and studying inscriptions, from 歐陽修's 《集古錄》 (1063) to modern catalogues.

### Works register (`pb-works`, `data/registers/works.xml`, standOff/listBibl)

```xml
<bibl xml:id="work-000123" type="work">
  <title xml:lang="zh">金石萃編</title>
  <title xml:lang="zh-Latn-x-pinyin">Jinshi cuibian</title>
  <author><persName corresp="person-000042">王昶</persName></author>
  <date type="compiled" when="1805" cert="high">嘉慶十年</date>
  <extent unit="juan">160</extent>
  <bibl type="edition" xml:id="work-000123-ed-01">
    <edition>1805 刻本</edition><date when="1805"/><publisher>經訓堂</publisher>
  </bibl>
  <relatedItem type="supplements" target="work-000045"/>
  <note type="source">vault provenance (lossless unparsed content)</note>
</bibl>
```

- `@type="work"` distinguishes the authority record from nested `@type="edition"` bibls and from `pb-bibl` bibliography entries.
- `<date type="compiled">`: graded precision — `@when` (exact year), `@notBefore`/`@notAfter` (era-derived range), `@cert="low"` (dynasty-only). Literal content preserved. Work date fallback: if no `<date type="compiled">`, the API uses the earliest edition `<date @when>`.
- `<relatedItem @type>`: `supplements | corrects | recompiles | models-on`. Inbound relations are *derived*, never stored twice (voice inversion: "supplemented-by" = query on `relatedItem[@type='supplements'][@target=id]`).
- `<respStmt><resp @key="sino:role:collab"/>` for non-author contributors (variant scribes, compilers).
- `@corresp` in `pb-bibl` bibliography entries points to the work authority: `<bibl xml:id="bibl-yzjsh" corresp="work-000002">`. Policy: bibliography register = citable short-form references in apparatus (`<bibl corresp="bibl-yzjsh">`); works register = full authority with editions and attestations.

### Inscription authority register (`pb-jinshi`, `data/registers/jinshi.xml`, standOff/listObject)

```xml
<object xml:id="insc-000007">
  <objectIdentifier>
    <objectName type="main" xml:lang="zh">乙瑛碑</objectName>
    <objectName type="sort" xml:lang="zh-Latn-x-pinyin">Yi Ying bei</objectName>
    <objectName type="alt">漢魯相乙瑛請置百石卒史碑</objectName>
    <idno type="corpus">E000123</idno>
  </objectIdentifier>
  <history><origin>
    <origDate when="0153" cert="high">永興元年</origDate>
    <origPlace corresp="place-…"/>
  </origin></history>
  <additional>
    <surrogates>
      <bibl type="rubbing"><ref target="https://…npm…"/></bibl>
    </surrogates>
    <listBibl type="attestations">
      <bibl corresp="work-000045">
        <citedRange unit="juan">13</citedRange>
        <title type="title-in-work">魯相乙瑛碑</title>
        <note>有跋</note>
      </bibl>
    </listBibl>
  </additional>
</object>
```

- Attestations live on the inscription as the single source of truth. The work's "inscriptions recorded" list is derived by `jinshi:inscriptions-in-work`.
- `@corresp` on `<bibl>` inside `listBibl[@type='attestations']` points to the work authority id.
- `idno @type="corpus"` links to an EpiDoc edition when one exists. Corpus side: `msIdentifier/idno @type="jinshi"` (value `insc-NNNNNN`) in workspace docs.

### Person lifespans (merged into `persons.xml`)

```xml
<person xml:id="person-000042">
  <birth when="1725"/><death when="1806"/>          <!-- exact: "1725–1806" -->
  <floruit notBefore="1796" notAfter="1820" cert="low">fl. 嘉慶</floruit>  <!-- era-derived -->
</person>
```

Graded precision (from import): `YYYY–YYYY` → birth/death (`exact`); `fl. <era>` → floruit span resolved from nianhao.xml (`floruit`); dynasty-only → floruit = dynasty span, `@cert="low"`; `?–?` / unknown → no dates (excluded from timelines). Literals preserved as element content.

### Timeline data model and rendering

- API `GET /api/sino/chronology` returns JSON `{dynasties, persons, works}` from TEI dates + dynasty taxonomy.
- Route is under `/api/sino/` to avoid the `/{docid}` catch-all in `lib/api.json` (which uses `allowReserved: true` on the path parameter).
- Person bars: solid fill = exact/partial; hatched fill (`url(#fh-full)`) = floruit or era-estimated.
- Work markers: solid diamond = `cert="high"` (exact); translucent = `cert="medium"` or `approx`.
- Attestation strip reads `data-year` attributes from `.work-date` spans (numeric ISO year), not the Chinese literal — avoids parsing era names in the browser.

## Stone Sutras corpus 石經 **[M-S1]**

Buddhist stone-sutra and Buddha-name inscriptions imported directly from the
**stonesutras.org** research dataset (`/Users/sassmann/Documents/sutras-data/`,
custom `exist-db catalog` ns + TEI transcriptions). Pilot site: **Hongdingshan 洪頂山
(HDS)**, Northern Qi. The source split maps onto the §-frame's *text ≠ support ≠ place*
non-negotiable as a **three-way** import:

| source (sutras-data) | EpiWen target | home |
|---|---|---|
| catalog `@type="site"` (`HDS_site.xml`) | `<place>` (geo, WGS84 — **swap** the source's lon,lat → `lat lon`) | merged into `registers/places.xml` **and** a per-place `data/places/place-*.xml` (the store `/api/places` + the map read) |
| catalog `@type="inscription"` (`HDS_11` …) | `<object type="sutra" xml:id="sutra-NNNNNN">` | **new register** `registers/sutras.xml` (`pb-sutras`) |
| docs transcription (`<catalog xlink:href>` / `<text xml:id>`) | full EpiDoc edition | `data/workspace/{catalog-id}.xml` |

- **Separate register**, not merged into 石刻總目 (`jinshi.xml`): the stone-sutra corpus is archaeological (transcriptions + Taishō), distinct from the attestation-based jinshi catalogue. `sutra-` id space, own nav/section/detail (`templates/sutra{,s}.html`), own routes (`/sutras`, `/api/sutras`).
- **Linkage**: authority `idno[@type='corpus']` = edition id · edition `idno[@type='jinshi']` = `sutra-NNNNNN` (reuses the jinshi cross-ref machinery) · inscription `origPlace/@corresp` = `place-…`.
- **Authority `<object>` idno set**: `corpus` (edition), `genre` (`sino:typeins:*`), `taisho` (one per `T_*` ref), `sutra-corpus` (site), `corpus-loc` (`HDS 11; lon,lat`). Dating: `origDate` with `@when` **or** `@notBefore/@notAfter` (ranges), `@n` = reign-era literal (e.g. `天保元年至河清三年`), `@period` resolved from the era literal (north/south disambiguator) falling back to a northern-preferring year lookup against `dynasty.xml`.
- **Genre heuristic**: name ends 佛/菩薩 → `foming` (佛名, Buddha-name); contains 經 / has a Sanskrit title → `kejing`; else `tiji`.
- **Editions** mirror `workspace/demo-zaoxiangji.xml` so they clear `scripts/validate-epidoc.sh` (EpiDoc RNG; only `listWit`/`witness` tolerated). Edition bodies carry the zh transcription as `div[@type='edition' xml:space='preserve']` (`lb/@n` preserved; editorial wrappers `persName`/`supplied reason="lost"`/`unclear` flattened to **text-only** — EpiDoc rejects nested wrappers and `lb` inside them); the en parallel div → `div[@type='translation']`.
- **Vocab additions**: `typeins.xml` `foming` 佛名; `material.xml` `baiyunyan` 白雲岩 (dolomite); `objtyp.xml` `jingshi` 經石.
- **Importer**: `scripts/import-sutras-data.py --site HDS` (idempotent; `scripts/sutras-id-map.json`). Pilot only; the full 605-inscription / 4,978-doc corpus is the next milestone.

## §11 Provenance & verification layer 溯源・核验 **[M-E1, Epiwen workshop]**

The Epiwen workshop frames two demands *beyond* EpiDoc: (a) a CIDOC-CRM **entity/relation ontology** on top of the document (the five entities E-TXT/E-SUP/E-PRD/E-WIT/E-ED), and (b) an **epistemic discipline** — every claim source-anchored (溯源), errors made visible rather than silently single-point-patched (自污染), and contested claims carried as attributed, queryable data with adversarial verification (核验). This layer implements the highest-value, gate-safe slice of both, exercised by the live Hongdingshan corpus.

### Verification state machine (核验, draft-by-default)

- `revisionDesc/@status` ∈ `draft | reviewed | verified`. **Draft-by-default**: imported / AI-drafted editions are `draft` (unverified) until a human deliberately promotes them. `reviewed` = adversarially checked; `verified` = human-confirmed.
- The `<change>` trail is **append-only** (the permanent audit trail). `api:postprocess` (custom-api.xql) preserves the *full* change history and snapshots `@status` onto each save's `<change>`; it previously dropped every change except `@type='created'`, which silently destroyed history — the self-pollution failure mode this layer exists to prevent. **[fix]**
- Provenance anchor (溯源): the importer stamps `<change … source="stonesutras:{cat-id}">` so every imported edition records where it came from.
- **Editor**: a status select in `templates/parts/edit/verification.html` (`revisionDesc/@status`). **Display**: a `.verify-badge` on the sutra detail + list + the `/api/sutras/all` `status` field (read live from the edition via `idno[@type='corpus']` — single source of truth, no stale copy).
- **Implements:** `modules/custom-api.xql` (append-only `revisionDesc` case) · `verification.html` status select + i18n `form.status-*` · `templates/sutra.html` + `modules/registers-api.xql` (badge, list, API) · `resources/css/registers-theme.css`. Test: `test/cypress/e2e/gui/editor-verification.cy.js`.

### One support → many texts (E-SUP) **[Epiwen object-model §2]**

- A moya field carries many inscriptions on distinct surfaces; "same site" ≠ "same support" (per-inscription coordinates scatter across the mountain). The catalog id encodes the real support: `HDS_9.1 … HDS_9.16` are 16 texts on support `HDS_9`.
- Encoded as `idno[@type='support']` on the authority `<object>` (the support grouping key = catalog base id before the dot). The sutra detail derives **"other texts on this support"** by querying siblings sharing the key. Singletons show no section.
- **Implements:** `import-sutras-data.py` (support key) · `templates/sutra.html` (derived sibling list) · i18n `sutras.same-support`. Test: `register-sutras.cy.js`.

### Structured certainty for contested attributions (the 安道一 case) **[Epiwen §13]**

- The calligrapher (書丹) is a *scholarly attribution* (the research catalog's producer field), not signed on the stone — the contestable-claim case. The 僧安道壹 Hongdingshan attributions (e.g. `sutra-000003 僧安道壹銘讚`, editions HDS_3/4/8/16.x) are famously debated.
- Encoded as `@cert="low"` on the `<persName xml:id="prod-shu">` **plus** a structured `<certainty target="#prod-shu" locus="value" degree="0.5" resp="#stonesutras">` with a `<desc>` rationale. Home = `<origin>` (= E-PRD, the production event, Epiwen §3) — so the doubt about *who carried out the 書丹 role* sits with the act, and the name string stays clean. Both survive the EpiDoc gate and the save pipeline.
- `<certainty>` is **not** valid in `respStmt`/`titleStmt` under tei-epidoc.rng (it is in `<origin>` and `<persName>`); the `<origin>` placement is the chosen, name-clean home. **[schema-conformance]**
- **Implements:** `import-sutras-data.py` (cert + certainty). Test: `register-sutras.cy.js`.

### Deferred (documented, not yet built)

- **E-PRD as a standoff `<event>`** with role-typed `P14` participants (Epiwen §12): v1 keeps the flat `titleStmt/respStmt` editing surface; the production *event* + CRM `@ref="crm:…"` CURIEs are v1.x (open fork #4, "assert CRM now vs later").
- **金石 compendium-as-witness double-modeling** (`biblStruct` in both `listWit` and `listBibl`, Epiwen §14): 録文 stay `listBibl[@type='transmission']`; apparatus `@wit` keying grows with the apparatus build-out.
- **殘石 `<join>`/`<msFrag>`** (Epiwen §14): no live-corpus pressure (HDS is single-surface moya) and it collides with EDEp's `@fragments` mechanism (§9 divergence #6) — needs design reconciliation first.

## Milestone map

| Milestone | Implements from this contract |
|---|---|
| M5 | All vocabulary files (§1 dynasty, §3 paleography, §8 objtyp/typeins/material/decor, §9 roles/preservation/languages) |
| M6 | Dating service + form (§1), nianhao.xml authority |
| M7 | Template extensions (origDate attrs, layout, handNote, listWit, charDecl, dimensions, respStmt, textpart/damage snippets, lzh defaults, listPrefixDef), editor parts, roundtrip fixture |
| M8 | Registers: person entry shape + nym system, place entry shape + period names + WGS84 (§6–7) |
| M9 | Rendition set + vertical preview, variant-char display, zh UI |
| M-J1–M-J5 | §10: works register, inscription authority register, person lifespans, timelines |
| M-S1 | Stone Sutras corpus: separate `sutras` register, site→place, transcription→edition; `import-sutras-data.py` (pilot: Hongdingshan) |
| M-E1 | §11 Provenance & verification layer: verification state machine (`revisionDesc/@status`, draft-by-default, append-only trail), one-support-many-texts (`idno[@type='support']`), structured `<certainty>` for contested attributions |
