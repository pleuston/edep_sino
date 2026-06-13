#!/usr/bin/env python3
"""
EpiWen — import-sutras-data.py  (M-S1)

Import the stonesutras.org research dataset (real catalog + TEI XML) into EpiWen.
This is the DIRECT-XML importer (cf. import-jinshi.py, which reads Obsidian markdown).

Pilot scope: one site, full-stack. For a site PREFIX (e.g. HDS = Hongdingshan):
    catalog/{PREFIX}_site.xml   (type="site")        → a <place> merged into registers/places.xml
    catalog/{PREFIX}_*.xml      (type="inscription")  → <object type="sutra"> in registers/sutras.xml
    docs/**/{PREFIX}_*.xml      (TEI transcription)    → a full EpiDoc edition in data/workspace/

The three-way split honours doc/sino-model.md's "text ≠ support ≠ place":
    site = place (geo)   ·   inscription = authority record   ·   transcription = edition (the carved text)

Linkage:  edition idno[@type='jinshi'] = sutra-NNNNNN  ·  authority idno[@type='corpus'] = edition id
          ·  inscription origPlace/@corresp = place-…

Usage:
    python3 scripts/import-sutras-data.py [--site HDS] [--dry-run]

Options:
    --source PATH   stonesutras-data root (default: /Users/sassmann/Documents/sutras-data)
    --site CODE     site prefix to import (default: HDS)
    --data-pkg PATH data-pkg directory (default: data-pkg)
    --id-map PATH   id map (default: scripts/sutras-id-map.json)
    --report PATH   report output (default: scripts/sutras-import-report.md)
    --dry-run       parse only; write nothing

Reuses helpers from import-jinshi.py (xe, _pad_year, id-map, _next_id) via importlib.
"""

import sys
import re
import json
import argparse
import importlib.util
import xml.etree.ElementTree as ET
from pathlib import Path

# ── Reuse helpers from import-jinshi.py ───────────────────────────────────────
_spec = importlib.util.spec_from_file_location(
    'import_jinshi', Path(__file__).parent / 'import-jinshi.py')
ij = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(ij)
xe = ij.xe
_pad_year = ij._pad_year
load_id_map_raw = ij.load_id_map
save_id_map = ij.save_id_map
_next_id = ij._next_id

# ── Constants ─────────────────────────────────────────────────────────────────

CAT_NS   = 'http://exist-db.org/ns/catalog'
TEI_NS   = 'http://www.tei-c.org/ns/1.0'
XLINK    = '{http://www.w3.org/1999/xlink}'
XMLNS    = '{http://www.w3.org/XML/1998/namespace}'
INDENT   = '    '
DEFAULT_SOURCE = '/Users/sassmann/Documents/sutras-data'
# Fixed timestamp keeps generated editions byte-identical across re-runs (idempotency).
CREATED  = '2026-06-12T00:00:00Z'

# Per-site metadata for the pilot (place id + pinyin + modern region).
# Generalising pinyin romanisation is out of scope; sites are added here as imported.
SITE_META = {
    'HDS': {'place_id': 'place-hongdingshan', 'pinyin': 'Hongdingshan',
            'region_zh': '山東', 'province': 'shandong', 'country': 'cn',
            'dynasty': 'beiqi'},  # all Hongdingshan carvings are Northern Qi
}

# Northern-Qi (and neighbouring) reign eras → dynasty xml:id, for @period resolution.
# The reign-era literal is the only reliable north/south disambiguator for the 6th c.
ERA2DYN = {
    '天保': 'beiqi', '乾明': 'beiqi', '皇建': 'beiqi', '太寧': 'beiqi',
    '大寧': 'beiqi', '河清': 'beiqi', '天統': 'beiqi', '武平': 'beiqi',
    '隆化': 'beiqi', '承光': 'beiqi',
    '武定': 'dongwei', '天平': 'dongwei', '元象': 'dongwei', '興和': 'dongwei',
    '大統': 'xiwei',
    '保定': 'beizhou', '天和': 'beizhou', '建德': 'beizhou', '宣政': 'beizhou',
    '武成': 'beizhou',
    '開皇': 'sui', '仁壽': 'sui', '大業': 'sui',
}


# ── XML local-name helpers (catalog files mix catalog-ns + TEI-ns) ────────────

def lname(el):
    t = el.tag
    return t.rsplit('}', 1)[-1] if isinstance(t, str) else ''


def child(el, name):
    """First direct child with the given local name."""
    if el is None:
        return None
    return next((c for c in el if lname(c) == name), None)


def children(el, name):
    if el is None:
        return []
    return [c for c in el if lname(c) == name]


def descend(el, *names):
    """Follow a path of local names from el (first match at each step)."""
    cur = el
    for n in names:
        cur = child(cur, n)
        if cur is None:
            return None
    return cur


def axml_lang(el):
    return el.get(XMLNS + 'lang') or el.get('lang') or ''


def axlink(el):
    return el.get(XLINK + 'href') or el.get('href') or ''


def axml_id(el):
    return el.get(XMLNS + 'id') or ''


def itext(el):
    """Concatenated, whitespace-normalised text of an element (for titles/labels)."""
    if el is None:
        return ''
    return re.sub(r'\s+', ' ', ''.join(el.itertext())).strip()


def strip_quotes(s):
    return s.strip().strip('“”"\'') if s else ''


def clean_year(s):
    """Return (padded-4-digit-year or '', uncertain?). Tolerates '556?', '~556', etc."""
    if not s:
        return '', False
    uncertain = '?' in s or '~' in s or '約' in s
    digits = re.sub(r'[^0-9-]', '', s)
    if not digits or digits == '-':
        return '', uncertain
    return _pad_year(digits), uncertain


def clean_num(s):
    """Numeric string for @quantity (tolerates '*14' = approximate, '14.0', '~14')."""
    if not s:
        return ''
    m = re.search(r'\d+(?:\.\d+)?', str(s))
    return m.group(0) if m else ''


# ── id allocation ─────────────────────────────────────────────────────────────

def load_id_map(path):
    p = Path(path)
    if p.exists():
        data = json.loads(p.read_text(encoding='utf-8'))
    else:
        data = {}
    data.setdefault('sutra-inscriptions', {})
    data.setdefault('places', {})
    data.setdefault('editions', {})
    return data


def assign_sutra_id(id_map, cat_id):
    m = id_map['sutra-inscriptions']
    if cat_id not in m:
        m[cat_id] = _next_id(m.values(), 'sutra-')
    return m[cat_id]


# ── natural sort for catalog ids (HDS_2 < HDS_9 < HDS_9.1 < HDS_10) ───────────

def natkey(cat_id):
    parts = re.split(r'[_.]', cat_id)
    key = []
    for p in parts:
        key.append((0, int(p)) if p.isdigit() else (1, p))
    return key


# ── date / dynasty resolution ─────────────────────────────────────────────────

def resolve_period(literal, lo, hi, dynasties):
    """Return a sino:dynasty:* CURIE. Prefer the reign-era literal; fall back to a
    northern-preferring year lookup against dynasty.xml ranges."""
    if literal:
        for era, dyn in ERA2DYN.items():
            if era in literal:
                return f'sino:dynasty:{dyn}'
    yrs = [y for y in (lo, hi) if y is not None]
    if not yrs:
        return ''
    mid = sum(yrs) // len(yrs)
    hits = [d for d in dynasties if d['from'] <= mid <= d['to']]
    if not hits:
        return ''
    if 386 <= mid <= 589:
        northern = [d for d in hits if d['zh'][:1] in ('北', '東', '西')]
        if northern:
            hits = northern
    hits.sort(key=lambda d: d['to'] - d['from'])  # narrowest range wins ties
    return hits[0]['curie']


def load_dynasties(data_pkg):
    p = Path(data_pkg) / 'data/taxonomy/dynasty.xml'
    out = []
    if not p.exists():
        return out
    root = ET.parse(p).getroot()
    for cat in root.iter():
        if lname(cat) != 'category':
            continue
        n = cat.get('n', '')
        curie = cat.get('corresp', '')
        zh = next((itext(c) for c in cat if lname(c) == 'catDesc'
                   and axml_lang(c) == 'zh'), '')
        m = re.match(r'(-?\d+):(-?\d+)', n)
        if m and curie:
            out.append({'curie': curie, 'zh': zh,
                        'from': int(m.group(1)), 'to': int(m.group(2))})
    return out


def load_nianhao(data_pkg):
    """Load nianhao.xml → list of era dicts for reverse ISO→era:year lookup."""
    p = Path(data_pkg) / 'data/taxonomy/nianhao.xml'
    out = []
    if not p.exists():
        return out
    root = ET.parse(p).getroot()
    for era in root:
        if era.tag != 'era':
            continue
        out.append({
            'name': era.get('name', ''),
            'dynasty': era.get('dynasty', ''),
            'from': int(era.get('from', '0')),
            'to': int(era.get('to', '0')),
        })
    return out


def iso_to_when_custom(iso_year_str, period_curie, nianhao_list):
    """Return 'era:reign_year' for a single-point ISO year, or '' if ambiguous.

    Prefers the era whose dynasty matches the given @period CURIE, then picks
    the narrowest range among ties so we get the specific Northern-Qi era rather
    than a homonymous era from another state.
    """
    if not iso_year_str or not nianhao_list:
        return ''
    try:
        iso = int(iso_year_str)
    except ValueError:
        return ''
    period_short = period_curie.rsplit(':', 1)[-1] if period_curie else ''
    # collect all eras covering this ISO year
    candidates = [e for e in nianhao_list if e['from'] <= iso <= e['to']]
    if not candidates:
        return ''
    # prefer those whose dynasty maps to the expected period
    preferred = [e for e in candidates
                 if ERA2DYN.get(e['name']) == period_short]
    pool = preferred if preferred else candidates
    # among the pool, pick the narrowest era (most specific)
    pool.sort(key=lambda e: e['to'] - e['from'])
    best = pool[0]
    reign_year = iso - best['from'] + 1
    return f"{best['name']}:{reign_year}"


# ── parse a catalog SITE file → place dict ────────────────────────────────────

def parse_site(path, site_code):
    root = ET.parse(path).getroot()
    header = child(root, 'header')
    name_zh = name_en = ''
    for t in children(header, 'title'):
        if axml_lang(t) == 'zh' and not name_zh:
            name_zh = itext(t)
        elif axml_lang(t) == 'en' and not name_en:
            name_en = itext(t)
    prov_zh = next((itext(p) for p in children(header, 'province')
                    if axml_lang(p) == 'zh'), '')
    # geo: <coordinates srsName="EPSG:4326">lon, lat</coordinates>  (→ swap to "lat lon")
    geo = ''
    coords_el = None
    for el in root.iter():
        if lname(el) == 'coordinates':
            coords_el = el
            break
    if coords_el is not None and coords_el.text:
        nums = re.findall(r'-?\d+\.?\d*', coords_el.text)
        if len(nums) >= 2:
            geo = f'{nums[1]} {nums[0]}'  # lon,lat → lat lon
    meta = SITE_META.get(site_code, {})
    region_zh = meta.get('region_zh') or re.sub(r'省\s*$', '', prov_zh).strip()
    pinyin = meta.get('pinyin') or re.sub(r'^Mount\s+', '', name_en).strip() or site_code
    place_id = meta.get('place_id') or ('place-' + re.sub(r'[^a-z0-9]+', '',
                                        pinyin.lower()))
    return {
        'site': site_code,
        'place_id': place_id,
        'name_zh': name_zh,
        'pinyin': pinyin,
        'geo': geo,
        'region_zh': region_zh,
        'name_en': name_en,
        'province': meta.get('province', ''),
        'country': meta.get('country', 'cn'),
    }


# ── parse a catalog INSCRIPTION file → dict ───────────────────────────────────

def parse_inscription(path, dynasties, nianhao=None, site_dynasty=''):
    root = ET.parse(path).getroot()
    cat_id = axml_id(root)
    site = root.get('site', '')
    header = child(root, 'header')

    # Titles
    title_zh = title_en = title_abbr = title_sa = ''
    for t in children(header, 'title'):
        lang = axml_lang(t)
        typ = t.get('type', '')
        txt = itext(t)
        if lang == 'zh' and typ == 'given' and not title_zh:
            title_zh = txt
        elif lang == 'sa' and not title_sa:
            title_sa = txt
        elif typ == 'abbreviated' and not title_abbr:
            title_abbr = txt
        elif lang == 'en' and not title_en:
            title_en = txt
    name_zh = strip_quotes(title_zh) or cat_id
    name_en = strip_quotes(title_en)

    # Date (scoped strictly to header/date/gregorian — char engraving also uses point/range)
    date_el = child(header, 'date')
    greg = child(date_el, 'gregorian')
    point = itext(child(greg, 'point')) if greg is not None else ''
    rng = child(greg, 'range') if greg is not None else None
    lo = rng.get('lower') if rng is not None else ''
    hi = rng.get('upper') if rng is not None else ''
    given_el = child(date_el, 'given')
    literal = itext(given_el)
    src = given_el.get('source', '') if given_el is not None else ''

    when_y, when_unc = clean_year(point)
    nb_y, nb_unc = clean_year(lo)
    na_y, na_unc = clean_year(hi)
    uncertain = when_unc or nb_unc or na_unc
    lo_i = int(nb_y) if nb_y else None
    hi_i = int(na_y) if na_y else None
    pt_i = int(when_y) if when_y else None
    period = resolve_period(literal, pt_i if pt_i else lo_i, hi_i, dynasties)
    # If the literal is absent (uncertain archaeological estimate), dynasty-span lookup may
    # pick a neighbouring state. Override with the site's known dynasty when provided.
    if not literal and site_dynasty and not period:
        period = f'sino:dynasty:{site_dynasty}'
    elif not literal and site_dynasty:
        # prefer site dynasty if the resolved period is implausible (not in ERA2DYN for this site)
        period_short = period.rsplit(':', 1)[-1] if period else ''
        site_curie = f'sino:dynasty:{site_dynasty}'
        if period_short and period_short != site_dynasty:
            period = site_curie
    # when-custom (era:year) — only for single-point dates, so the form can pre-fill on reopen
    when_custom = (iso_to_when_custom(when_y, period, nianhao or '')
                   if when_y and not nb_y else '')

    # Producer (signatory) — usually empty; recorded if present
    producer = itext(child(header, 'producer'))

    # Physical description
    phys = child(root, 'physicalDescription')
    dims = child(phys, 'dimensions')
    height = dims.get('height', '') if dims is not None else ''
    width = dims.get('width', '') if dims is not None else ''
    cd = child(phys, 'character-dimensions')
    cols = rows = 0
    char_h = []
    for ch in children(cd, 'character'):
        try:
            cols = max(cols, int(float(ch.get('column') or 0)))
            rows = max(rows, int(float(ch.get('row') or 0)))
            if ch.get('height'):
                char_h.append(float(ch.get('height')))
        except ValueError:
            pass

    def label_pair(tag):
        el = child(phys, tag)
        zh = next((itext(l) for l in children(el, 'label')
                   if axml_lang(l) == 'zh'), '')
        en = next((itext(l) for l in children(el, 'label')
                   if axml_lang(l) == 'en'), '')
        return zh, en

    cond_zh, cond_en = label_pair('condition')
    mineral_zh, mineral_en = label_pair('mineral')
    technique_zh, technique_en = label_pair('technique')

    # References
    taisho = []
    transmission = []   # value="transcription"
    bibliography = []   # value="discussion"
    rubbing_note_zh = rubbing_note_en = ''
    refs = child(root, 'references')
    rub = child(refs, 'rubbing')
    if rub is not None:
        rubbing_note_zh = next((itext(n) for n in children(rub, 'note')
                                if axml_lang(n) == 'zh'), '')
        rubbing_note_en = next((itext(n) for n in children(rub, 'note')
                                if axml_lang(n) == 'en'), '')
    for r in children(refs, 'ref'):
        href = axlink(r)
        pages = itext(child(r, 'pages'))
        if r.get('type') == 'taisho':
            taisho.append(href)
        elif r.get('value') == 'transcription':
            transmission.append({'key': href, 'pages': pages})
        elif r.get('value') == 'discussion':
            bibliography.append({'key': href, 'pages': pages})

    # File links (images)
    images = []
    fd = child(root, 'fileDescription')
    for ln in children(fd, 'link'):
        images.append({'type': ln.get('type', ''), 'href': axlink(ln),
                       'caption': next((itext(c) for c in children(ln, 'caption')
                                        if axml_lang(c) == 'en'), '')})

    # Location
    loc = child(root, 'location')
    coord = child(loc, 'coordinates')
    coord_txt = (coord.text or '').strip() if coord is not None else ''
    coord_norm = ''
    if coord_txt:
        nums = re.findall(r'-?\d+\.?\d*', coord_txt)
        if len(nums) >= 2:
            coord_norm = f'{nums[0]},{nums[1]}'  # keep source lon,lat for the idno note

    # Genre heuristic
    if name_zh and (name_zh[-1] in ('佛', '尊') or name_zh.endswith('菩薩')):
        genre = 'foming'           # Buddha-name inscription (大字佛名)
    elif '經' in name_zh or title_sa:
        genre = 'kejing'           # sutra engraving
    else:
        genre = 'tiji'             # colophon / occasional

    num = cat_id[len(site) + 1:] if site and cat_id.startswith(site + '_') else cat_id
    # support key = catalog base id before the dot (HDS_9.1 → HDS_9): one physical
    # support carries many texts (doc/sino-model.md §11, E-SUP).
    support = cat_id.split('.')[0]

    return {
        'cat_id':       cat_id,
        'site':         site,
        'num':          num,
        'support':      support,
        'name_zh':      name_zh,
        'name_en':      name_en,
        'alt_names':    [a for a in (name_en, strip_quotes(title_abbr),
                                     strip_quotes(title_sa)) if a],
        'title_sa':     strip_quotes(title_sa),
        'producer':     producer,
        'when':         when_y,
        'notBefore':    nb_y,
        'notAfter':     na_y,
        'date_literal': literal,
        'when_custom':  when_custom,
        'date_cert':    'low' if (uncertain or src == 'discussion'
                                  or (nb_y and not when_y)) else 'high',
        'genre':        genre,
        'period':       period,
        'height':       height,
        'width':        width,
        'cols':         cols,
        'rows':         rows,
        'char_h':       char_h,
        'cond_zh':      cond_zh,
        'cond_en':      cond_en,
        'mineral_zh':   mineral_zh,
        'mineral_en':   mineral_en,
        'technique_zh': technique_zh,
        'taisho':       taisho,
        'transmission': transmission,
        'bibliography': bibliography,
        'rubbing_note_zh': rubbing_note_zh,
        'rubbing_note_en': rubbing_note_en,
        'images':       images,
        'coord':        coord_norm,
    }


# ── material mapping (mineral label → sino:material:* CURIE) ───────────────────

MINERAL2MAT = {
    '白雲岩': 'baiyunyan', 'dolomite': 'baiyunyan',
    '石灰岩': 'shihuiyan', 'limestone': 'shihuiyan',
    '花崗岩': 'huagangyan', 'granite': 'huagangyan',
    '砂岩': 'shayan', 'sandstone': 'shayan',
    '大理石': 'dalishi', 'marble': 'dalishi',
}


def material_curie(insc):
    for key in (insc['mineral_zh'].rstrip('？?'), insc['mineral_en'].rstrip('？?')):
        key = key.strip()
        if key in MINERAL2MAT:
            return f'sino:material:{MINERAL2MAT[key]}'
    return ''


# ── authority <object> generator (sutras.xml) ─────────────────────────────────

def sutra_object_xml(insc, sutra_id, place_id, site_pinyin, has_edition, depth=3):
    d, d1, d2, d3 = (INDENT * depth, INDENT * (depth + 1),
                     INDENT * (depth + 2), INDENT * (depth + 3))
    sort_name = insc['name_en'] or f'{insc["site"]} {insc["num"]}'
    lines = [f'{d}<object xml:id="{sutra_id}" type="sutra">']
    lines.append(f'{d1}<objectIdentifier>')
    lines.append(f'{d2}<objectName type="main" xml:lang="zh">{xe(insc["name_zh"])}</objectName>')
    lines.append(f'{d2}<objectName type="sort">{xe(sort_name)}</objectName>')
    for alt in insc['alt_names']:
        lang = ' xml:lang="en"' if re.match(r'^[\x00-\x7f]', alt) else ''
        lines.append(f'{d2}<objectName type="alt"{lang}>{xe(alt)}</objectName>')
    if has_edition:
        lines.append(f'{d2}<idno type="corpus">{xe(insc["cat_id"])}</idno>')
    if insc.get('genre'):
        lines.append(f'{d2}<idno type="genre">{xe(insc["genre"])}</idno>')
    for t in insc['taisho']:
        lines.append(f'{d2}<idno type="taisho">{xe(t)}</idno>')
    lines.append(f'{d2}<idno type="sutra-corpus">{xe(site_pinyin)}</idno>')
    loc = f'{insc["site"]} {insc["num"]}'
    if insc['coord']:
        loc += f'; {insc["coord"]}'
    lines.append(f'{d2}<idno type="corpus-loc">{xe(loc)}</idno>')
    # support grouping key (doc/sino-model.md §11, E-SUP one-support-many-texts):
    # the catalog base id before the dot is one physical support — HDS_9 carries
    # HDS_9.1…HDS_9.16. Editions sharing this key are texts on the same support.
    lines.append(f'{d2}<idno type="support">{xe(insc["support"])}</idno>')
    lines.append(f'{d1}</objectIdentifier>')
    # history / origin
    has_date = insc['when'] or insc['notBefore'] or insc['notAfter'] or insc['date_literal']
    lines.append(f'{d1}<history>')
    lines.append(f'{d2}<origin>')
    if has_date:
        attrs = ''
        if insc['when']:
            attrs += f' when="{insc["when"]}"'
        else:
            if insc['notBefore']:
                attrs += f' notBefore="{insc["notBefore"]}"'
            if insc['notAfter']:
                attrs += f' notAfter="{insc["notAfter"]}"'
        if insc['date_literal']:
            attrs += f' n="{xe(insc["date_literal"])}"'
        if insc.get('when_custom'):
            attrs += f' when-custom="{xe(insc["when_custom"])}"'
        if insc['period']:
            attrs += f' period="{insc["period"]}"'
        if insc['date_cert']:
            attrs += f' cert="{insc["date_cert"]}"'
        attrs += ' datingMethod="#gregorian-converted"'
        lines.append(f'{d3}<origDate{attrs}>{xe(insc["date_literal"])}</origDate>')
    lines.append(f'{d3}<origPlace corresp="{place_id}"/>')
    lines.append(f'{d2}</origin>')
    lines.append(f'{d1}</history>')
    lines.append(f'{d}</object>')
    return lines


_SUTRAS_HEADER = '''\
<?xml version="1.0" encoding="UTF-8"?>
<TEI xmlns="http://www.tei-c.org/ns/1.0" xml:id="pb-sutras">
    <teiHeader>
        <fileDesc>
            <titleStmt><title>EpiWen register: stone sutras 石經</title></titleStmt>
            <publicationStmt><p>Authority register of Buddhist stone-sutra and Buddha-name
                inscriptions. Entry shape: doc/sino-model.md §10. One entry per inscription
                (not per monument); the carrying site is a place (registers/places.xml) and the
                carved text is a corpus edition (data/workspace).</p></publicationStmt>
            <sourceDesc><p>Imported by scripts/import-sutras-data.py from the stonesutras.org
                research dataset.</p></sourceDesc>
        </fileDesc>
    </teiHeader>
    <standOff>
        <listObject type="sutra">'''

_SUTRAS_FOOTER = '''\
        </listObject>
    </standOff>
</TEI>'''


def write_sutras_xml(objects, path):
    lines = [_SUTRAS_HEADER]
    for obj_lines in objects:
        lines.extend(obj_lines)
    lines.append(_SUTRAS_FOOTER)
    Path(path).write_text('\n'.join(lines) + '\n', encoding='utf-8')


# ── places.xml merge (preserve existing hand seeds) ───────────────────────────

def merge_place(place, places_path):
    p = Path(places_path)
    text = p.read_text(encoding='utf-8')
    if f'xml:id="{place["place_id"]}"' in text:
        return False
    block = [
        f'{INDENT*3}<place xml:id="{place["place_id"]}" type="feature">',
        f'{INDENT*4}<placeName type="main" xml:lang="zh">{xe(place["name_zh"])}</placeName>',
        f'{INDENT*4}<placeName xml:lang="zh-Latn-pinyin">{xe(place["pinyin"])}</placeName>',
        f'{INDENT*4}<placeName type="sort">{xe(place["pinyin"])}</placeName>',
    ]
    if place['geo']:
        block.append(f'{INDENT*4}<location><geo>{xe(place["geo"])}</geo></location>')
    if place['region_zh']:
        block.append(f'{INDENT*4}<region type="sheng" xml:lang="zh">{xe(place["region_zh"])}</region>')
    en = place['name_en'] or place['pinyin']
    block.append(f'{INDENT*4}<note xml:lang="en">{xe(en)}, {xe(place["region_zh"])}; '
                 f'Buddhist stone-sutra and Buddha-name carvings. Source: stonesutras.org.</note>')
    block.append(f'{INDENT*3}</place>')
    new_text = text.replace(f'{INDENT*2}</listPlace>',
                            '\n'.join(block) + f'\n{INDENT*2}</listPlace>', 1)
    p.write_text(new_text, encoding='utf-8')
    return True


def write_place_file(place, places_dir):
    """Write the per-place file read by /api/places + the map ($config:places-root).
    Mirrors the existing data/places/place-*.xml shape."""
    lines = [
        f'<place xmlns="http://www.tei-c.org/ns/1.0" xml:id="{place["place_id"]}">',
        f'{INDENT}<placeName type="findspot">{xe(place["name_zh"])}</placeName>',
        f'{INDENT}<placeName type="modern">{xe(place["name_zh"])} {xe(place["pinyin"])}</placeName>',
        f'{INDENT}<placeName type="sort">{xe(place["pinyin"])}</placeName>',
    ]
    if place['province']:
        lines.append(f'{INDENT}<region type="province">{xe(place["province"])}</region>')
    if place['region_zh']:
        lines.append(f'{INDENT}<region type="modern">{xe(place["region_zh"])}</region>')
    lines.append(f'{INDENT}<country>{xe(place["country"])}</country>')
    if place['geo']:
        lines.append(f'{INDENT}<location>')
        lines.append(f'{INDENT*2}<geo>{xe(place["geo"])}</geo>')
        lines.append(f'{INDENT}</location>')
    lines.append(f'{INDENT}<ptr type="tgaz" target=""/>')
    lines.append('</place>')
    Path(places_dir).mkdir(parents=True, exist_ok=True)
    (Path(places_dir) / f'{place["place_id"]}.xml').write_text(
        '\n'.join(lines) + '\n', encoding='utf-8')


# ── transcription → EpiDoc edition body ───────────────────────────────────────

def _clean_seg(s):
    """Drop line-break indentation but keep inline (CJK) spacing."""
    return re.sub(r'\s*\n\s*', '', s) if s else ''


def render_inline(el, out):
    if el.text:
        out.append(xe(_clean_seg(el.text)))
    for c in el:
        ln = lname(c)
        if ln == 'lb':
            out.append(f'\n<lb n="{xe((c.get("n") or "").strip())}"/>')
            if c.text:
                out.append(xe(_clean_seg(c.text)))
        elif ln == 'p':
            render_inline(c, out)
        # Editorial wrappers carry FLATTENED text only (no nested elements, no inner
        # <lb>) — EpiDoc rejects e.g. <persName> spanning an <lb> or nested <unclear>.
        elif ln == 'persName':
            t = itext(c)
            if t:
                out.append('<persName>' + xe(t) + '</persName>')
        elif ln == 'foreign':
            lang = axml_lang(c)
            la = f' xml:lang="{xe(lang)}"' if lang else ''
            t = itext(c)
            if t:
                out.append(f'<foreign{la}>' + xe(t) + '</foreign>')
        elif ln == 'supplied':
            t = itext(c)
            if t:
                out.append('<supplied reason="lost">' + xe(t) + '</supplied>')
        elif ln == 'unclear':
            t = itext(c)
            if t:
                out.append('<unclear>' + xe(t) + '</unclear>')
        elif ln in ('gap',):
            qty = (c.get('quantity') or c.get('extent') or '').strip()
            q = f' quantity="{xe(qty)}"' if qty.isdigit() else ''
            out.append(f'<gap reason="lost"{q} unit="character"/>')
        elif ln in ('damage',):
            t = itext(c)
            if t:
                out.append('<unclear>' + xe(t) + '</unclear>')
        else:
            render_inline(c, out)  # flatten unknown wrappers, keep their text + lb
        if c.tail:
            out.append(xe(_clean_seg(c.tail)))


def build_edition_body(doc_root):
    """Return (edition_inner, translation_paras) from a transcription TEI doc."""
    text_el = child(doc_root, 'text')
    body = child(text_el, 'body')
    zh_div = next((dv for dv in children(body, 'div')
                   if axml_lang(dv) == 'zh'), None)
    en_div = next((dv for dv in children(body, 'div')
                   if axml_lang(dv) == 'en'), None)
    edition = ''
    if zh_div is not None:
        out = []
        render_inline(zh_div, out)
        edition = ''.join(out).strip('\n')
    trans = []
    if en_div is not None:
        for p in children(en_div, 'p'):
            t = itext(p)
            if t:
                trans.append(t)
        if not trans:
            t = itext(en_div)
            if t:
                trans.append(t)
    return edition, trans


# ── EpiDoc edition generator (workspace/*.xml), modelled on demo-zaoxiangji.xml ─

def edition_xml(insc, sutra_id, place_id, edition_inner, translation):
    genre = insc['genre']
    mat = material_curie(insc)
    L = []
    a = L.append
    a('<?xml version="1.0" encoding="UTF-8"?>')
    a('<?xml-model href="http://epidoc.stoa.org/schema/latest/tei-epidoc.rng" '
      'schematypens="http://relaxng.org/ns/structure/1.0"?>')
    a(f'<TEI xmlns="http://www.tei-c.org/ns/1.0" xml:id="{insc["cat_id"]}">')
    a('    <teiHeader>')
    a('        <fileDesc>')
    a('            <titleStmt>')
    a(f'                <title xml:lang="zh">{xe(insc["name_zh"])}</title>')
    if insc['name_en']:
        a(f'                <title xml:lang="en">{xe(insc["name_en"])}</title>')
    a('                <editor/>')
    if insc['producer']:
        # The calligrapher (書丹) is a SCHOLARLY attribution (the research catalog's
        # producer field), not signed on the stone — the contestable-claim case the
        # certainty model exists for (doc/sino-model.md §11; the 僧安道壹 Hongdingshan
        # attributions are famously debated). Encode the doubt as structured, attributed,
        # queryable data: @cert on the name + a <certainty> with degree, locus and source.
        a('                <respStmt>')
        a('                    <resp key="sino:role:shu">書丹</resp>')
        a(f'                    <persName xml:id="prod-shu" cert="low">{xe(insc["producer"])}</persName>')
        a('                </respStmt>')
    else:
        a('                <respStmt>')
        a('                    <resp key="sino:role:ke">刻</resp>')
        a('                    <persName key="">未詳</persName>')
        a('                </respStmt>')
    a('            </titleStmt>')
    a('            <publicationStmt>')
    a('                <authority>EpiWen</authority>')
    a('                <availability>')
    a('                    <licence target="http://creativecommons.org/licenses/by-sa/4.0/">CC BY-SA 4.0</licence>')
    a('                </availability>')
    a('            </publicationStmt>')
    a('            <sourceDesc>')
    a('                <msDesc>')
    a('                    <msIdentifier>')
    a(f'                        <repository>{xe(insc["site"])}（摩崖原石）</repository>')
    a(f'                        <idno type="inventory">{xe(insc["cat_id"])}</idno>')
    a(f'                        <idno type="EDEp">{xe(insc["cat_id"])}</idno>')
    a(f'                        <idno type="jinshi">{sutra_id}</idno>')
    a('                        <idno type="TM"/>')
    a('                    </msIdentifier>')
    summary = insc['name_en'] or insc['name_zh']
    a(f'                    <msContents class="sino:typeins:{genre}">')
    a(f'                        <summary>{xe(summary)}</summary>')
    a('                    </msContents>')
    a('                    <physDesc>')
    a('                        <objectDesc form="sino:medium:keshi">')
    a('                            <supportDesc>')
    a('                                <support>')
    a('                                    <objectType ref="sino:objtyp:moya"/>')
    if mat:
        a(f'                                    <material ref="{mat}"/>')
    w_num, h_num = clean_num(insc['width']), clean_num(insc['height'])
    if w_num or h_num:
        a('                                    <dimensions unit="cm">')
        if w_num:
            a(f'                                        <width quantity="{w_num}"/>')
        if h_num:
            a(f'                                        <height quantity="{h_num}"/>')
        a('                                    </dimensions>')
    a('                                </support>')
    if insc['cond_zh'] or insc['cond_en']:
        cond = ' / '.join([x for x in (insc['cond_zh'], insc['cond_en']) if x])
        a(f'                                <condition>{xe(cond)}</condition>')
    a('                            </supportDesc>')
    if insc['cols'] or insc['rows']:
        cols = insc['cols'] or 1
        wl = insc['rows'] or 1
        a('                            <layoutDesc>')
        a(f'                                <layout columns="{cols}" writtenLines="{wl}" '
          f'style="writing-mode: vertical-rl">')
        note = insc['technique_zh']
        a(f'                                    <ab>{xe(note)}</ab>' if note
          else '                                    <ab/>')
        a('                                </layout>')
        a('                            </layoutDesc>')
    a('                        </objectDesc>')
    if insc['char_h']:
        lo = int(min(insc['char_h']))
        hi = int(max(insc['char_h']))
        a('                        <handDesc>')
        a('                            <handNote scope="letterHeight">')
        a('                                <dimensions>')
        a(f'                                    <height min="{lo}" max="{hi}"/>')
        a('                                </dimensions>')
        a('                            </handNote>')
        a('                        </handDesc>')
    a('                    </physDesc>')
    a('                    <history>')
    a('                        <origin>')
    attrs = ''
    if insc['when']:
        attrs += f' when="{insc["when"]}"'
    else:
        if insc['notBefore']:
            attrs += f' notBefore="{insc["notBefore"]}"'
        if insc['notAfter']:
            attrs += f' notAfter="{insc["notAfter"]}"'
    if insc['date_literal']:
        attrs += f' n="{xe(insc["date_literal"])}"'
    if insc.get('when_custom'):
        attrs += f' when-custom="{xe(insc["when_custom"])}"'
    if insc['period']:
        attrs += f' period="{insc["period"]}"'
    if insc['date_cert']:
        attrs += f' cert="{insc["date_cert"]}"'
    attrs += ' datingMethod="#gregorian-converted"'
    a(f'                            <origDate{attrs}>{xe(insc["date_literal"])}</origDate>')
    a(f'                            <origPlace corresp="{place_id}"/>')
    if insc['producer']:
        # Structured certainty (doc/sino-model.md §11, Epiwen §13) about the calligrapher
        # attribution (書丹, #prod-shu in titleStmt). Home = <origin> = the production event
        # (E-PRD, Epiwen §3), so the doubt about who carried out the 書丹 role sits with the
        # act. @degree/@locus/@resp make the contested 僧安道壹/法洪 attribution queryable.
        a('                            <certainty target="#prod-shu" locus="value" degree="0.5" resp="#stonesutras">')
        a('                                <desc>書丹 attribution is a scholarly conjecture (stonesutras.org), not signed on the stone; contested.</desc>')
        a('                            </certainty>')
    a('                        </origin>')
    a('                    </history>')
    a('                </msDesc>')
    # Rubbing as a first-class witness
    if insc['rubbing_note_zh'] or insc['rubbing_note_en']:
        rn = insc['rubbing_note_en'] or insc['rubbing_note_zh']
        a('                <listWit>')
        a('                    <witness type="rubbing">')
        a('                        <msDesc>')
        a('                            <msIdentifier><repository>山東省石刻藝術博物館</repository></msIdentifier>')
        a('                            <physDesc><objectDesc><supportDesc>')
        a('                                <support>紙本墨拓</support>')
        a(f'                                <condition>{xe(rn[:160])}</condition>')
        a('                            </supportDesc></objectDesc></physDesc>')
        a('                        </msDesc>')
        a('                    </witness>')
        a('                </listWit>')
    # Bibliography
    a('                <listBibl>')
    if insc['transmission']:
        a('                    <listBibl type="transmission">')
        for r in insc['transmission']:
            cr = (f'<citedRange unit="page">{xe(r["pages"])}</citedRange>'
                  if r['pages'] else '')
            a(f'                        <bibl><ref target="#{xe(r["key"])}"/>{cr}</bibl>')
        a('                    </listBibl>')
    else:
        a('                    <listBibl type="transmission"/>')
    a('                    <listBibl type="previousEditions"/>')
    if insc['bibliography']:
        a('                    <listBibl type="bibliography">')
        for r in insc['bibliography']:
            cr = (f'<citedRange unit="page">{xe(r["pages"])}</citedRange>'
                  if r['pages'] else '')
            a(f'                        <bibl><ref target="#{xe(r["key"])}"/>{cr}</bibl>')
        a('                    </listBibl>')
    else:
        a('                    <listBibl type="bibliography"/>')
    if insc['images']:
        a('                    <listBibl type="images">')
        for im in insc['images']:
            a(f'                        <bibl><ref target="{xe(im["href"])}">{xe(im["caption"] or im["type"])}</ref></bibl>')
        a('                    </listBibl>')
    else:
        a('                    <listBibl type="images"/>')
    a('                </listBibl>')
    a('            </sourceDesc>')
    a('        </fileDesc>')
    a('        <encodingDesc>')
    a('            <p>Encoded following EpiDoc guidelines and the EpiWen encoding conventions. '
      'Imported from stonesutras.org.</p>')
    a('        </encodingDesc>')
    a('        <profileDesc>')
    a('            <textClass>')
    a('                <keywords scheme="https://edh.ub.uni-heidelberg.de/edep/religion">')
    a('                    <term ref="sino:religion:fojiao"/>')
    a('                </keywords>')
    a('            </textClass>')
    a('            <langUsage>')
    a('                <language ident="lzh" ana="main"/>')
    a('            </langUsage>')
    a('        </profileDesc>')
    # draft-by-default (doc/sino-model.md §11, 核验): imported = unverified until a
    # human promotes it; the change records the upstream source (溯源 provenance anchor).
    a(f'        <revisionDesc status="draft">')
    a(f'            <change type="created" status="draft" when="{CREATED}"'
      f' who="import-sutras-data" source="stonesutras:{xe(insc["cat_id"])}"/>')
    a('        </revisionDesc>')
    a('    </teiHeader>')
    a('    <text>')
    a('        <body>')
    a('            <div type="edition" xml:lang="lzh" xml:space="preserve">')
    a('<ab>')
    a(edition_inner if edition_inner else f'<lb n="1"/>{xe(insc["name_zh"])}')
    a('</ab>')
    a('            </div>')
    a('            <div type="apparatus"/>')
    if translation:
        a('            <div type="translation" xml:lang="en">')
        for para in translation:
            a(f'                <p>{xe(para)}</p>')
        a('            </div>')
    a('        </body>')
    a('    </text>')
    a('</TEI>')
    return '\n'.join(L) + '\n'


# ── report ────────────────────────────────────────────────────────────────────

def write_report(site, place, inscs, n_editions, missing_docs, path, dry_run):
    lines = [
        '# EpiWen — stone-sutra import report',
        '',
        f'*Generated by scripts/import-sutras-data.py{" (dry-run)" if dry_run else ""} '
        f'— site `{site}`*',
        '',
        '## Summary',
        '',
        '| Item | Value |',
        '|---|---|',
        f'| Site (place) | {place["name_zh"]} ({place["pinyin"]}) → `{place["place_id"]}` |',
        f'| Inscriptions (authority objects) | {len(inscs)} |',
        f'| Editions generated (with transcription) | {n_editions} |',
        f'| Inscriptions without transcription | {len(missing_docs)} |',
        '',
    ]
    if missing_docs:
        lines += ['## Inscriptions without a transcription doc (authority-only)', '']
        lines += [f'- `{m}`' for m in missing_docs]
        lines.append('')
    lines += ['## Inscriptions', '', '| sutra-id | cat-id | name | date | genre | taishō | edition |',
              '|---|---|---|---|---|---|---|']
    for ins in inscs:
        date = ins['when'] or f'{ins["notBefore"]}–{ins["notAfter"]}'
        lines.append(f'| {ins["sutra_id"]} | {ins["cat_id"]} | {ins["name_zh"]} | '
                     f'{date} | {ins["genre"]} | {len(ins["taisho"])} | '
                     f'{"✓" if ins["has_edition"] else "—"} |')
    Path(path).write_text('\n'.join(lines) + '\n', encoding='utf-8')


# ── main ──────────────────────────────────────────────────────────────────────

def main():
    ap = argparse.ArgumentParser(description='Import stonesutras.org data into EpiWen.')
    ap.add_argument('--source', default=DEFAULT_SOURCE)
    ap.add_argument('--site', default='HDS')
    ap.add_argument('--data-pkg', default='data-pkg')
    ap.add_argument('--id-map', default='scripts/sutras-id-map.json')
    ap.add_argument('--report', default='scripts/sutras-import-report.md')
    ap.add_argument('--dry-run', action='store_true')
    args = ap.parse_args()

    source = Path(args.source)
    data_pkg = Path(args.data_pkg)
    site = args.site
    if not source.exists():
        print(f'ERROR: source not found: {source}', file=sys.stderr)
        sys.exit(1)

    id_map = load_id_map(args.id_map)
    dynasties = load_dynasties(data_pkg)
    nianhao = load_nianhao(data_pkg)

    # 1. Site → place
    site_file = source / 'catalog' / f'{site}_site.xml'
    if not site_file.exists():
        print(f'ERROR: site file not found: {site_file}', file=sys.stderr)
        sys.exit(1)
    place = parse_site(site_file, site)
    id_map['places'][site] = place['place_id']

    # 2. Inscriptions
    cat_files = sorted(
        [p for p in (source / 'catalog').glob(f'{site}_*.xml')
         if p.stem != f'{site}_site'],
        key=lambda p: natkey(p.stem))

    # 3. Transcription doc index (by stem) for this site
    doc_index = {}
    for d in (source / 'docs').rglob(f'{site}_*.xml'):
        doc_index.setdefault(d.stem, d)

    site_dynasty = SITE_META.get(site, {}).get('dynasty', '')
    inscs = []
    editions = {}          # cat_id → edition xml string
    missing_docs = []
    for cf in cat_files:
        insc = parse_inscription(cf, dynasties, nianhao, site_dynasty)
        insc['genre'] = insc.get('genre') or 'tiji'
        sutra_id = assign_sutra_id(id_map, insc['cat_id'])
        insc['sutra_id'] = sutra_id
        doc_path = doc_index.get(insc['cat_id'])
        has_edition = doc_path is not None
        insc['has_edition'] = has_edition
        if has_edition:
            doc_root = ET.parse(doc_path).getroot()
            ed_inner, trans = build_edition_body(doc_root)
            editions[insc['cat_id']] = edition_xml(
                insc, sutra_id, place['place_id'], ed_inner, trans)
        else:
            missing_docs.append(insc['cat_id'])
        inscs.append(insc)

    # Sort objects by sutra id for stable output
    inscs_sorted = sorted(inscs, key=lambda x: x['sutra_id'])
    objects = [sutra_object_xml(ins, ins['sutra_id'], place['place_id'],
                                place['pinyin'], ins['has_edition'])
               for ins in inscs_sorted]

    print(f'Site {site}: place {place["place_id"]}; '
          f'{len(inscs)} inscriptions; {len(editions)} editions; '
          f'{len(missing_docs)} without transcription', file=sys.stderr)

    if not args.dry_run:
        save_id_map(id_map, args.id_map)
        sutras_path = data_pkg / 'data/registers/sutras.xml'
        places_path = data_pkg / 'data/registers/places.xml'
        ws_dir = data_pkg / 'data/workspace'
        sutras_path.parent.mkdir(parents=True, exist_ok=True)
        ws_dir.mkdir(parents=True, exist_ok=True)
        write_sutras_xml(objects, sutras_path)
        added = merge_place(place, places_path)
        write_place_file(place, data_pkg / 'data/places')
        for cat_id, xml in editions.items():
            (ws_dir / f'{cat_id}.xml').write_text(xml, encoding='utf-8')
        print(f'Wrote {sutras_path}', file=sys.stderr)
        print(f'places.xml: {"added " + place["place_id"] if added else "place already present"}',
              file=sys.stderr)
        print(f'Wrote {len(editions)} editions to {ws_dir}', file=sys.stderr)

    write_report(site, place, inscs_sorted, len(editions), missing_docs,
                 args.report, args.dry_run)
    print(f'Wrote {args.report}', file=sys.stderr)


if __name__ == '__main__':
    main()
