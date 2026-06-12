#!/usr/bin/env python3
"""
EpiWen — import-jinshi.py  (M-J2)

Import jinshi 金石學 data from the Obsidian vault into the EpiWen TEI registers.

Usage:
    python3 scripts/import-jinshi.py --vault /path/to/vault [options]

Options:
    --vault PATH        Vault root (required)
    --data-pkg PATH     data-pkg directory (default: data-pkg)
    --id-map PATH       ID map file (default: scripts/jinshi-id-map.json)
    --report PATH       Report output (default: scripts/jinshi-import-report.md)
    --dry-run           Parse only; do not write files

Vault structure read (read-only):
    {vault}/knowledge base/Texts/Epigraphy 金石學/*.md   — works
    {vault}/knowledge base/Texts/Epigraphy 金石學/Editions/*.md — editions
    {vault}/knowledge base/Inscriptions/*.md              — inscriptions
    {vault}/knowledge base/Persons/*.md                   — persons

Outputs written:
    {data_pkg}/data/registers/works.xml   (complete, vault-derived)
    {data_pkg}/data/registers/jinshi.xml  (complete, vault-derived + preserved non-vault)
    {data_pkg}/data/registers/persons.xml (merged: existing + vault dates + new authors)
    {report}  (import statistics and unparsed-line log)
"""

import sys
import re
import json
import argparse
import xml.etree.ElementTree as ET
from pathlib import Path
from collections import defaultdict

# ── Vault directory layout ────────────────────────────────────────────────────

VAULT_WORKS     = Path('knowledge base/Texts/Epigraphy 金石學')
VAULT_EDITIONS  = VAULT_WORKS / 'Editions'
VAULT_INSCR     = Path('knowledge base/Inscriptions')
VAULT_PERSONS   = Path('knowledge base/Persons')

# ── Constants ─────────────────────────────────────────────────────────────────

TEI_NS = 'http://www.tei-c.org/ns/1.0'
XML_NS = 'http://www.w3.org/XML/1998/namespace'
INDENT = '    '

# Known rubbing institution URL patterns
RUBBING_HOSTS = (
    'digitalarchive.npm.gov.tw',
    'colbase.nich.go.jp',
    'id.lib.harvard.edu',
    'ids.lib.harvard.edu',
    'digicoll.lib.berkeley.edu',
    'estampages.efeo.fr',
    'i-repository.net',
)

# Dynasty date spans for floruit resolution
DYNASTY_SPANS = {
    '先秦': (-1100, -221), '秦': (-221, -206),
    '漢': (-206, 220),    '前漢': (-206, 9),   '西漢': (-206, 9),
    '後漢': (25, 220),    '東漢': (25, 220),
    '三國': (220, 280),   '魏': (220, 265),
    '晉': (265, 420),     '西晉': (265, 316),  '東晉': (317, 420),
    '南北朝': (420, 589), '北朝': (420, 581),  '南朝': (420, 589),
    '北魏': (386, 534),   '隋': (581, 618),
    '唐': (618, 907),     '五代': (907, 960),
    '宋': (960, 1279),    '北宋': (960, 1127), '南宋': (1127, 1279),
    '遼': (916, 1125),    '金': (1115, 1234),
    '元': (1271, 1368),   '明': (1368, 1644),
    '清': (1616, 1912),   '民國': (1912, 1949),
    'Qing': (1616, 1912), 'Song': (960, 1279),
    'Tang': (618, 907),   'Han': (-206, 220),
    'Ming': (1368, 1644), 'Yuan': (1271, 1368),
}

# ── Compiled regexes ──────────────────────────────────────────────────────────

_FM_RE = re.compile(r'^---[ \t]*\n(.*?)\n---[ \t]*\n', re.DOTALL)
_WIKILINK_RE = re.compile(r'\[\[([^\]|#]+?)(?:\|[^\]]*)?\]\]')
_ATTEST_RE = re.compile(
    r'^\s*[-*]\s*'
    r'[^\[\n]*'                              # optional prefix (emoji, category tags)
    r'\[\[(?P<link>[^\]|#]+?)(?:\|[^\]]*)?\]\]'
    r'\s*[—–-]+\s*'
    r'(?:「(?P<title>[^」]*)」\s*(?:[—–-]+\s*)?)?'
    r'(?P<rest>.*?)\s*$',
    re.UNICODE,
)
_MDLINK_RE   = re.compile(r'\[([^\]]*)\]\((https?://[^)]+)\)')
_YEAR4_RE    = re.compile(r'\b([12][0-9]{3})\b')
_FILENAME_RE = re.compile(
    r'^(?P<pinyin>[A-Za-zÀ-ÿ][A-Za-zÀ-ÿ\s]+?)\s+'
    r'(?P<zh>[一-鿿]{1,8})\s*'
    r'《(?P<title>[^》]+)》'
)

# Person filenames: "Pinyin Name 漢字" with optional trailing "(dates)" or ", Surname"
_PERSON_RE = re.compile(
    r'^(?P<pinyin>[A-Za-zÀ-ÿ][A-Za-zÀ-ÿ,\.\s]+?)\s+'
    r'(?P<zh>[一-鿿]{1,10})'
    r'(?:\s*[\(\（][^)\）]*[\)\）])?'
    r'\s*$'
)

# ── XML utilities ─────────────────────────────────────────────────────────────

def xe(s):
    """Escape XML text/attribute content."""
    if s is None:
        return ''
    return (str(s)
            .replace('&', '&amp;')
            .replace('<', '&lt;')
            .replace('>', '&gt;')
            .replace('"', '&quot;'))


def _xml_id(el):
    return el.get(f'{{{XML_NS}}}id', '')


# ── Frontmatter parser (YAML-lite) ────────────────────────────────────────────

def parse_fm(text):
    """Parse flat YAML frontmatter; returns dict."""
    m = _FM_RE.match(text)
    if not m:
        return {}
    result = {}
    cur_key = None
    for line in m.group(1).splitlines():
        s = line.strip()
        if not s or s.startswith('#'):
            continue
        if s.startswith('- '):
            val = s[2:].strip().strip('"\'')
            if cur_key is not None:
                v = result.get(cur_key)
                if isinstance(v, list):
                    v.append(val)
                else:
                    result[cur_key] = ([v, val] if v and v is not True
                                       else [val])
            continue
        if ':' in s:
            key, _, val = s.partition(':')
            key = key.strip()
            val = val.strip()
            if (val.startswith('"') and val.endswith('"')) or \
               (val.startswith("'") and val.endswith("'")):
                val = val[1:-1]
            cur_key = key
            if val in ('', '[]', 'null', '~'):
                result[key] = []
            elif val in ('true', 'True', 'yes'):
                result[key] = True
            elif val in ('false', 'False', 'no'):
                result[key] = False
            else:
                result[key] = val
    return result


def fm_str(fm, key):
    v = fm.get(key, '')
    return v if isinstance(v, str) else ''


def fm_list(fm, key):
    v = fm.get(key, [])
    if isinstance(v, list):
        return v
    return [v] if v else []


# ── ID map ────────────────────────────────────────────────────────────────────

def load_id_map(path):
    """Load or initialise the id map."""
    p = Path(path)
    if p.exists():
        return json.loads(p.read_text(encoding='utf-8'))
    return {'works': {}, 'inscriptions': {}, 'persons': {}}


def save_id_map(id_map, path):
    Path(path).write_text(
        json.dumps(id_map, ensure_ascii=False, indent=2, sort_keys=True),
        encoding='utf-8',
    )


def _next_id(existing_ids, prefix, width=6):
    """Return next sequential ID with zero-padded number."""
    used = set()
    pat = re.compile(rf'^{re.escape(prefix)}(\d+)$')
    for v in existing_ids:
        mo = pat.match(v)
        if mo:
            used.add(int(mo.group(1)))
    n = 1
    while n in used:
        n += 1
    return f'{prefix}{n:0{width}d}'


def assign_work_id(id_map, stem):
    if stem not in id_map['works']:
        id_map['works'][stem] = _next_id(id_map['works'].values(), 'work-')
    return id_map['works'][stem]


def assign_insc_id(id_map, stem):
    if stem not in id_map['inscriptions']:
        id_map['inscriptions'][stem] = _next_id(
            id_map['inscriptions'].values(), 'insc-')
    return id_map['inscriptions'][stem]


def person_slug(pinyin_name):
    """Derive a stable slug from a person's pinyin name."""
    s = pinyin_name.strip().lower()
    s = re.sub(r'[^a-z0-9]+', '-', s)
    return 'person-' + s.strip('-')


def assign_person_id(id_map, stem, pinyin_name):
    if stem not in id_map['persons']:
        slug = person_slug(pinyin_name)
        # Avoid collision
        existing = set(id_map['persons'].values())
        base = slug
        n = 2
        while slug in existing:
            slug = f'{base}-{n}'
            n += 1
        id_map['persons'][stem] = slug
    return id_map['persons'][stem]


# ── Alias map ─────────────────────────────────────────────────────────────────

def build_alias_map(vault):
    """
    Map every alias (wikilink target) → vault filename stem.
    Used for resolving attestation wikilinks to vault files.
    """
    alias_map = {}

    def _add(stem, aliases):
        alias_map[stem] = stem  # canonical
        for a in aliases:
            a = a.strip().strip('"\'')
            if a:
                alias_map[a] = stem

    # Works
    for p in (vault / VAULT_WORKS).glob('*.md'):
        if p.name.startswith('_') or p.parent.name == 'Editions':
            continue
        stem = p.stem
        text = p.read_text(encoding='utf-8', errors='ignore')
        fm = parse_fm(text)
        aliases = fm_list(fm, 'aliases')
        _add(stem, aliases)
        # Also add title-only form: 《Title》
        mo = re.search(r'《([^》]+)》', stem)
        if mo:
            alias_map[f'《{mo.group(1)}》'] = stem
            alias_map[mo.group(1)] = stem

    # Inscriptions
    for p in (vault / VAULT_INSCR).glob('*.md'):
        if p.name.startswith('_'):
            continue
        stem = p.stem
        text = p.read_text(encoding='utf-8', errors='ignore')
        fm = parse_fm(text)
        aliases = fm_list(fm, 'aliases')
        _add(stem, aliases)

    return alias_map


# ── Date parsing ──────────────────────────────────────────────────────────────

def load_nianhao(data_pkg):
    """Return {era_name: (from_year, to_year)} from nianhao.xml, or {}."""
    p = Path(data_pkg) / 'data/taxonomy/nianhao.xml'
    if not p.exists():
        return {}
    try:
        tree = ET.parse(p)
        root = tree.getroot()
        era_map = {}
        for era in root.findall('.//era'):
            name = era.get('name', '')
            alt  = era.get('alt', '')
            frm  = era.get('from')
            to   = era.get('to')
            if name and frm and to:
                span = (int(frm[:4]), int(to[:4]))
                era_map[name] = span
                for a in alt.split():
                    if a:
                        era_map[a] = span
        return era_map
    except Exception:
        return {}


def parse_dates(dates_str, nianhao):
    """
    Parse a person dates string; return dict with keys:
      birth (int|None), death (int|None),
      floruit_from (int|None), floruit_to (int|None),
      cert ('high'|'medium'|'low'), literal (str)
    """
    s = str(dates_str).strip()
    result = dict(birth=None, death=None,
                  floruit_from=None, floruit_to=None,
                  cert='high', literal=s)
    if not s or s in ('?', '?–?', '?—?', '?-?', '', 'n/a', 'unknown'):
        return result

    # YYYY–YYYY  or  YYYY–YYYY.X  (birth–death)
    mo = re.match(
        r'^(?P<b>[12]\d{3})\s*[–—-]+\s*(?P<d>[12]\d{3})(?:\.\S+)?$', s)
    if mo:
        result['birth'] = int(mo.group('b'))
        result['death'] = int(mo.group('d'))
        return result

    # YYYY–  (birth only)
    mo = re.match(r'^(?P<b>[12]\d{3})\s*[–—-]+\s*$', s)
    if mo:
        result['birth'] = int(mo.group('b'))
        return result

    # –YYYY  (death only)
    mo = re.match(r'^\s*[–—-]+\s*(?P<d>[12]\d{3})$', s)
    if mo:
        result['death'] = int(mo.group('d'))
        return result

    # fl. <something>
    mo = re.match(r'^fl\.\s*(?P<rest>.+)', s)
    if mo:
        rest = mo.group('rest').strip()
        result['cert'] = 'low'
        # Try era name first
        for key in [rest, rest.split()[0], rest.split('(')[0].strip()]:
            if key in nianhao:
                frm, to = nianhao[key]
                result['floruit_from'] = frm
                result['floruit_to']   = to
                result['cert']         = 'medium'
                return result
        # Try dynasty
        for key in [rest, rest.split()[0], rest.split('(')[0].strip()]:
            if key in DYNASTY_SPANS:
                frm, to = DYNASTY_SPANS[key]
                result['floruit_from'] = frm
                result['floruit_to']   = to
                return result
        # Unknown floruit — keep it
        return result

    # Bare dynasty name
    if s in DYNASTY_SPANS:
        frm, to = DYNASTY_SPANS[s]
        result['floruit_from'] = frm
        result['floruit_to']   = to
        result['cert'] = 'low'
        return result

    return result


# ── Work file import ──────────────────────────────────────────────────────────

def _extract_section(text, *headers):
    """Return text of the first matching markdown section (# or ## Header).
    Single-hash (top-level) sections are supported in addition to ## subsections.
    The section body ends at the next heading of the same or higher level."""
    for hdr in headers:
        for prefix in (r'##+ ', r'# '):
            pat = re.compile(
                rf'^{prefix}{re.escape(hdr)}\s*\n(.*?)(?=^#|\Z)',
                re.MULTILINE | re.DOTALL,
            )
            mo = pat.search(text)
            if mo:
                return mo.group(1).strip()
    return ''


def import_works(vault, id_map, alias_map):
    """Parse all work files; return list of work dicts + report stats."""
    works_dir = vault / VAULT_WORKS
    if not works_dir.exists():
        return [], {'count': 0, 'errors': []}

    stats = {'count': 0, 'with_year': 0, 'with_author': 0, 'errors': []}
    works = []

    for p in sorted(works_dir.glob('*.md')):
        if p.name.startswith('_') or p.parent != works_dir:
            continue
        stem = p.stem
        try:
            text = p.read_text(encoding='utf-8', errors='ignore')
            fm   = parse_fm(text)
            work = _parse_work(stem, text, fm, id_map, alias_map)
            if work:
                works.append(work)
                stats['count'] += 1
                if work.get('year_when'):
                    stats['with_year'] += 1
                if work.get('author_zh'):
                    stats['with_author'] += 1
        except Exception as e:
            stats['errors'].append(f'{stem}: {e}')

    return works, stats


def _parse_work(stem, text, fm, id_map, alias_map):
    """Extract structured data from a work markdown file."""
    work_id = assign_work_id(id_map, stem)

    # Title from filename
    mo = _FILENAME_RE.match(stem)
    if mo:
        author_pinyin = mo.group('pinyin').strip()
        author_zh     = mo.group('zh').strip()
        title_zh      = mo.group('title').strip()
    else:
        # Anonymous / title-only filename
        tmo = re.search(r'《([^》]+)》', stem)
        title_zh      = tmo.group(1) if tmo else stem
        author_pinyin = ''
        author_zh     = ''

    # Pinyin title from aliases — strip author-pinyin prefix if present
    title_pinyin = ''
    for alias in fm_list(fm, 'aliases'):
        if re.match(r'^[A-Za-z]', alias) and '《' not in alias:
            candidate = alias
            if author_pinyin and candidate.lower().startswith(author_pinyin.lower() + ' '):
                candidate = candidate[len(author_pinyin) + 1:]
            title_pinyin = candidate
            break
    # Pinyin override from id-map takes priority
    pinyin_override = id_map.get('title_pinyin_overrides', {}).get(work_id, '')
    if pinyin_override:
        title_pinyin = pinyin_override

    # Edition list (will be filled later from edition files)
    edition_list = _parse_inline_editions(text)

    # Year: look in title prose / aliases for 4-digit year
    year_when, year_cert, year_label = _extract_work_year(text, stem, edition_list)

    # Compiled-date override from id-map takes priority (hand-curated seeds)
    date_override = id_map.get('work_date_overrides', {}).get(work_id)
    if date_override:
        year_when  = date_override.get('when', year_when)
        year_cert  = date_override.get('cert', 'high')
        year_label = date_override.get('label', str(year_when))

    # Juan count from Overview prose
    juan = _extract_juan(text)

    return {
        'id':            work_id,
        'vault_stem':    stem,
        'title_zh':      title_zh,
        'title_pinyin':  title_pinyin,
        'author_zh':     author_zh,
        'author_pinyin': author_pinyin,
        'author_id':     '',          # resolved later
        'year_when':     year_when,
        'year_cert':     year_cert,
        'year_label':    year_label,
        'juan':          juan,
        'editions':      edition_list,
        'relations':     _parse_work_relations(text, alias_map, id_map),
    }


# Maps bold-label keywords (lower-cased, stripped) → TEI relatedItem/@type
_REL_LABEL_MAP = {
    'models on':            'models-on',
    'modelled on':          'models-on',
    'built on':             'models-on',
    'based on':             'models-on',
    'supplements':          'supplements',
    'supplement of':        'supplements',
    '补正':                  'supplements',
    '補正':                  'supplements',
    '补正 / supplement of': 'supplements',
    '補正 / supplement of': 'supplements',
    'corrects':             'corrects',
    'correction of':        'corrects',
    'recompiles':           'recompiles',
    'recompilation of':     'recompiles',
}


def _parse_work_relations(text, alias_map, id_map):
    """Parse outbound inter-work relations from '# Relations to other works'."""
    section = _extract_section(text, 'Relations to other works', 'Relations')
    if not section:
        return []

    relations = []
    current_type = None
    current_links = []

    def _flush():
        if current_type:
            for link in current_links:
                wid = _resolve_work_id(link, alias_map, id_map)
                if wid and wid.startswith('work-'):
                    relations.append({'type': current_type, 'target_id': wid})

    for line in section.splitlines():
        stripped = line.strip()
        if stripped.startswith('-') or stripped.startswith('*'):
            _flush()
            current_links = []
            current_type = None
            # Detect the bold label at the start of this bullet
            label_mo = re.match(r'^[-*]\s+\*\*([^*]+)\*\*\s*[:/]?', stripped)
            if label_mo:
                label = label_mo.group(1).strip().lower().rstrip(':/')
                for key, rel_type in _REL_LABEL_MAP.items():
                    if key in label:
                        current_type = rel_type
                        break
            if current_type:
                current_links.extend(_WIKILINK_RE.findall(stripped))
        elif current_type and stripped and not stripped.startswith('#'):
            # Continuation of a multi-line bullet
            current_links.extend(_WIKILINK_RE.findall(stripped))

    _flush()
    return relations


def _parse_inline_editions(text):
    """Extract editions from the '## Editions' section (wikilinks)."""
    section = _extract_section(text, 'Editions', '### Editions')
    editions = []
    for line in section.splitlines():
        line = line.strip()
        if not (line.startswith('- ') or line.startswith('* ')):
            continue
        # Try to find a wikilink with edition label
        mo = re.search(r'\[\[([^\]|#]+?)(?:\|[^\]]*)?\]\]', line)
        if not mo:
            continue
        link_text = mo.group(1).strip()
        # Extract year from link text (e.g. "Editions/《...》 — 新文豐 (1977)")
        year_mo = re.search(r'\((\d{4})\)', link_text)
        year = int(year_mo.group(1)) if year_mo else None
        # Publisher extraction: after last ' — '
        parts = link_text.replace('/', '/').split(' — ')
        label = parts[-1].strip() if len(parts) > 1 else link_text.split('/')[-1].strip()
        editions.append({
            'label':         label,
            'year':          year,
            'publisher':     '',
            'in_collection': '',
            'vault_link':    link_text,
        })
    return editions


def _extract_work_year(text, stem, edition_list):
    """Best-effort year extraction; returns (year_when, cert, label) or (None,'','')."""
    # Year in filename: 《Title》 (YYYY)
    mo = re.search(r'\((\d{4})\)\s*$', stem)
    if mo:
        y = int(mo.group(1))
        return y, 'high', str(y)

    # Patterns in Overview prose: "compiled YYYY", "(YYYY)", 嘉慶十年（1805）
    greg_pat = re.compile(r'[（(](\d{4})[）)]')
    mo = greg_pat.search(text[:2000])  # first 2k chars = Overview area
    if mo:
        y = int(mo.group(1))
        if 600 <= y <= 1940:
            # Label: a tight era-year token right before the parenthesis
            # (嘉慶十年 / 光緒五年…), never a prose window.
            before = text[max(0, mo.start() - 20):mo.start()]
            m2 = re.search(r'([一-鿿]{2,4}[元一二三四五六七八九十廿卅]{1,4}年)\s*$', before)
            label = m2.group(1) if m2 else str(y)
            return y, 'medium', label

    # Earliest year from edition list
    years = [e['year'] for e in edition_list if e.get('year')]
    if years:
        y = min(years)
        return y, 'low', str(y)

    return None, '', ''


def _extract_juan(text):
    """Extract 卷 count from prose."""
    mo = re.search(r'(\d+)\s*(?:卷|juan)', text[:3000])
    if mo:
        n = int(mo.group(1))
        if 1 <= n <= 999:
            return n
    return None


# ── Edition file import ───────────────────────────────────────────────────────

def import_edition_files(vault, id_map, alias_map):
    """
    Parse all edition files; return dict mapping work alias → list[edition_dict].
    """
    ed_dir = vault / VAULT_EDITIONS
    if not ed_dir.exists():
        return {}
    result = defaultdict(list)

    for p in sorted(ed_dir.glob('*.md')):
        if p.name.startswith('_'):
            continue
        try:
            text = p.read_text(encoding='utf-8', errors='ignore')
            fm   = parse_fm(text)
            if fm.get('type') not in ('edition', 'edition', None, ''):
                # Skip non-edition meta files
                if fm.get('type') not in ('edition', True, ''):
                    t = str(fm.get('type', ''))
                    if t and 'edition' not in t.lower():
                        continue

            work_link = fm_str(fm, 'work')
            if not work_link:
                continue
            # Extract wikilink target
            wmo = _WIKILINK_RE.search(work_link)
            work_key = wmo.group(1).strip() if wmo else work_link.strip()

            year_str = fm_str(fm, 'year')
            year = int(year_str) if year_str and year_str.isdigit() else None

            edition = {
                'label':         p.stem,
                'year':          year,
                'publisher':     fm_str(fm, 'publisher'),
                'in_collection': _strip_wikilink(fm_str(fm, 'in_collection')),
                'vault_link':    work_key,
            }
            result[work_key].append(edition)
            # Also index under aliases
            if work_key in alias_map:
                result[alias_map[work_key]].append(edition)
        except Exception:
            pass

    return dict(result)


def _strip_wikilink(s):
    mo = _WIKILINK_RE.search(s)
    return mo.group(1).split('/')[-1].strip() if mo else s.strip()


# ── Inscription file import ───────────────────────────────────────────────────

def import_inscriptions(vault, id_map, alias_map):
    """Parse all inscription files; return list of inscription dicts + stats."""
    insc_dir = vault / VAULT_INSCR
    if not insc_dir.exists():
        return [], {'count': 0, 'att_total': 0, 'att_parsed': 0, 'unparsed': []}

    stats = {'count': 0, 'att_total': 0, 'att_parsed': 0, 'unparsed': []}
    inscriptions = []

    for p in sorted(insc_dir.glob('*.md')):
        if p.name.startswith('_'):
            continue
        stem = p.stem
        try:
            text = p.read_text(encoding='utf-8', errors='ignore')
            fm   = parse_fm(text)
            insc, n_total, n_parsed, unparsed = _parse_inscription(
                stem, text, fm, id_map, alias_map)  # id_map passed for corresp resolution
            inscriptions.append(insc)
            stats['count']      += 1
            stats['att_total']  += n_total
            stats['att_parsed'] += n_parsed
            stats['unparsed'].extend(unparsed)
        except Exception as e:
            stats['unparsed'].append(f'ERROR {stem}: {e}')

    return inscriptions, stats


def _parse_inscription(stem, text, fm, id_map, alias_map):
    insc_id = assign_insc_id(id_map, stem)  # also used for attestation work_id resolution

    # Names
    name_zh = fm_str(fm, 'title') or stem
    # Try to find a shorter main name
    mo = re.match(r'^([一-鿿《》]+)', stem)
    if mo:
        name_zh = mo.group(1).strip('《》')

    alt_names = [a.strip().strip('"\'') for a in fm_list(fm, 'aliases')
                 if a.strip() and not re.match(r'^[A-Za-z]', a.strip())]
    sort_name = next((a for a in fm_list(fm, 'aliases')
                      if re.match(r'^[A-Za-z]', a.strip())), '')

    # Date
    orig_when  = str(fm.get('date_year_gregorian', '')).strip()
    orig_when  = _pad_year(orig_when) if orig_when else ''
    dynasty    = fm_str(fm, 'dynasty')
    date_label = fm_str(fm, 'date_label') or (
        f'{dynasty}' if dynasty else '')

    # Origin place
    orig_place = fm_str(fm, 'origin_place') or ''

    # Attestations — prefer "Full list" section
    atts, n_total, n_parsed, unparsed = _parse_attestation_section(
        text, stem, alias_map, id_map)

    # Rubbings
    rubbings = _parse_rubbings(text)

    # Corpus link
    corpus_id = fm_str(fm, 'corpus_id') or ''

    return (
        {
            'id':         insc_id,
            'vault_stem': stem,
            'name_zh':    name_zh,
            'alt_names':  alt_names,
            'sort_name':  sort_name,
            'orig_when':  orig_when,
            'orig_place': orig_place,
            'dynasty':    dynasty,
            'date_label': date_label,
            'attestations': atts,
            'rubbings':   rubbings,
            'corpus_id':  corpus_id,
        },
        n_total, n_parsed, unparsed,
    )


def _pad_year(y):
    """Zero-pad a gregorian year to 4 digits (e.g. 153 → 0153)."""
    try:
        n = int(y)
        return f'{n:04d}' if n > 0 else str(n)
    except ValueError:
        return y


def _parse_attestation_section(text, stem, alias_map, id_map=None):
    # Prefer Full list, fall back to partial
    section = _extract_section(text,
                               'Attestations (Full list)',
                               'Attestations (full list)',
                               'Attestations')
    # Also gather attestation lines in the preamble of a top-level
    # "# Attestations" heading (before any ## sub-section).  Some files have
    # hand-curated lines there in addition to (or instead of) the ## subsection.
    top_mo = re.search(
        r'^# Attestations[^\n]*\n(.*?)(?=^#|\Z)',
        text, re.MULTILINE | re.DOTALL
    )
    if top_mo:
        preamble = top_mo.group(1)
        # Strip everything from the first ## heading onwards (that's the mined subsection)
        subsect_start = re.search(r'^##', preamble, re.MULTILINE)
        if subsect_start:
            preamble = preamble[:subsect_start.start()]
        section = preamble.strip() + '\n' + section
    atts      = []
    n_total   = 0
    n_parsed  = 0
    unparsed  = []

    for line in section.splitlines():
        stripped = line.strip()
        if not stripped.startswith('-') and not stripped.startswith('*'):
            continue
        # Skip rubbing lines (URLs)
        if 'http' in stripped and ']]' not in stripped:
            continue
        if '[[' not in stripped:
            continue
        # Skip internal project navigation links (not attestations)
        all_links = _WIKILINK_RE.findall(stripped)
        if not all_links:
            continue
        if all(lnk.startswith('_') or lnk.startswith('_wiki') for lnk in all_links):
            continue
        n_total += 1
        mo = _ATTEST_RE.match(stripped)
        if mo:
            link  = mo.group('link').strip()
            title = (mo.group('title') or '').strip()
            rest  = (mo.group('rest') or '').strip()
            # Resolve wikilink → vault stem → TEI work id
            work_id = _resolve_work_id(link, alias_map, id_map)
            atts.append({
                'work_link': link,
                'work_id':   work_id,
                'title':     title,
                'rest':      rest,
                'juan':      _extract_juan_from_rest(rest),
            })
            n_parsed += 1
        else:
            unparsed.append(f'{stem}: {stripped[:80]}')

    return atts, n_total, n_parsed, unparsed


def _resolve_work_id(link, alias_map, id_map=None):
    """Resolve a wikilink target to a TEI work xml:id via alias_map → id_map."""
    stem = alias_map.get(link, alias_map.get(link.strip(), ''))
    if stem and id_map is not None:
        return id_map.get('works', {}).get(stem, stem)
    return stem


def _extract_juan_from_rest(rest):
    """Try to pull a juan number from the attestation rest field."""
    mo = re.search(
        r'(?:卷|[Jj]uan)\s*(?:第\s*)?'
        r'([一二三四五六七八九十百千\d]+)',
        rest,
    )
    return mo.group(1) if mo else ''


def _parse_rubbings(text):
    """Extract rubbing URLs from # Rubbings section and inline links."""
    rubbings = []
    rubbing_section = _extract_section(text, 'Rubbings')
    for line in rubbing_section.splitlines():
        for mo in _MDLINK_RE.finditer(line):
            url = mo.group(2)
            if any(h in url for h in RUBBING_HOSTS):
                rubbings.append({
                    'label': mo.group(1).strip(),
                    'url':   url,
                })
    return rubbings


# ── Person file import ────────────────────────────────────────────────────────

def import_persons(vault, id_map, alias_map, nianhao):
    """Parse person files; return list of person dicts + stats."""
    pers_dir = vault / VAULT_PERSONS
    if not pers_dir.exists():
        return [], {'count': 0, 'with_dates': 0}

    stats   = {'count': 0, 'with_dates': 0}
    persons = []

    for p in sorted(pers_dir.glob('*.md')):
        if p.name.startswith('_'):
            continue
        stem = p.stem
        try:
            text = p.read_text(encoding='utf-8', errors='ignore')
            fm   = parse_fm(text)
            if fm.get('type') not in (
                    'work', True, None, '', '[[personAuthority]]',
                    'person', 'personAuthority'):
                t = str(fm.get('type', ''))
                # Only skip if clearly not a person
                if t and t not in ('[[personAuthority]]', 'person', ''):
                    if 'person' not in t.lower():
                        continue

            dates_str = fm_str(fm, 'dates')
            aliases   = fm_list(fm, 'aliases')

            # Extract zh name and pinyin from filename
            mo = _PERSON_RE.match(stem)
            if mo:
                pinyin = mo.group('pinyin').strip().rstrip(',')
                zh     = mo.group('zh').strip()
            elif re.match(r'^[一-鿿]', stem):
                # Bare zh-only filename
                zh     = re.sub(r'[\s（\(].+$', '', stem).strip()
                pinyin = ''
            else:
                continue

            person_id = assign_person_id(id_map, stem, pinyin or zh)
            dates     = parse_dates(dates_str, nianhao) if dates_str else {}

            persons.append({
                'id':       person_id,
                'stem':     stem,
                'zh':       zh,
                'pinyin':   pinyin,
                'aliases':  aliases,
                'dates':    dates,
            })
            stats['count'] += 1
            if dates.get('birth') or dates.get('floruit_from'):
                stats['with_dates'] += 1
        except Exception:
            pass

    return persons, stats


# ── Resolve author IDs in works ───────────────────────────────────────────────

def resolve_author_ids(works, persons, existing_person_map):
    """
    Fill work['author_id'] by matching author_zh against
    existing persons.xml and vault person list.
    """
    # Build lookup: zh_name → person_id
    lookup = dict(existing_person_map)  # from existing persons.xml
    for p in persons:
        if p['zh'] not in lookup:
            lookup[p['zh']] = p['id']

    for work in works:
        zh = work.get('author_zh', '')
        if zh and zh in lookup:
            work['author_id'] = lookup[zh]


# ── Merge edition files into works ───────────────────────────────────────────

def merge_editions(works, edition_files, alias_map):
    """Attach edition-file data to corresponding works."""
    # Build reverse map: work_stem → work
    by_stem = {w['vault_stem']: w for w in works}

    for work_key, editions in edition_files.items():
        # Resolve to a stem
        stem = alias_map.get(work_key, work_key)
        work = by_stem.get(stem)
        if not work:
            continue
        # Deduplicate by year+label
        existing = {(e.get('year'), e.get('label')[:30] if e.get('label') else '')
                    for e in work['editions']}
        for ed in editions:
            key = (ed.get('year'), (ed.get('label', '') or '')[:30])
            if key not in existing:
                work['editions'].append(ed)
                existing.add(key)

    # Sort editions by year within each work
    for w in works:
        w['editions'].sort(key=lambda e: e.get('year') or 9999)


# ── Preserve non-vault entries from existing jinshi.xml ─────────────────────

def load_preserved_objects(jinshi_path, vault_insc_ids):
    """
    Read existing jinshi.xml; return list of raw XML strings for
    <object> entries whose xml:id is NOT being replaced by vault data.
    """
    p = Path(jinshi_path)
    if not p.exists():
        return []
    try:
        ET.register_namespace('', TEI_NS)
        tree = ET.parse(p)
        root = tree.getroot()
        preserved = []
        for obj in root.findall(f'.//{{{TEI_NS}}}object'):
            obj_id = _xml_id(obj)
            if obj_id and obj_id not in vault_insc_ids:
                preserved.append(_et_to_dict(obj))
        return preserved
    except Exception:
        return []


def _et_to_dict(obj):
    """Convert a TEI <object> ET element to a simple dict for re-serialisation."""
    xml_id = _xml_id(obj)
    # Extract key fields
    def _find_text(tag):
        el = obj.find(f'.//{{{TEI_NS}}}{tag}')
        return el.text.strip() if el is not None and el.text else ''

    def _find_attr(tag, attr):
        el = obj.find(f'.//{{{TEI_NS}}}{tag}')
        return el.get(attr, '') if el is not None else ''

    # objectNames
    names = []
    for on in obj.findall(f'.//{{{TEI_NS}}}objectName'):
        names.append({
            'type':    on.get('type', ''),
            'lang':    on.get(f'{{{XML_NS}}}lang', ''),
            'text':    on.text.strip() if on.text else '',
        })

    # idno
    idnos = []
    for idno in obj.findall(f'.//{{{TEI_NS}}}idno'):
        idnos.append({
            'type': idno.get('type', ''),
            'text': idno.text.strip() if idno.text else '',
        })

    # origDate
    orig_date_el = obj.find(f'.//{{{TEI_NS}}}origDate')
    orig_date = {}
    if orig_date_el is not None:
        orig_date = {
            'when':   orig_date_el.get('when', ''),
            'cert':   orig_date_el.get('cert', ''),
            'method': orig_date_el.get('datingMethod', ''),
            'text':   orig_date_el.text.strip() if orig_date_el.text else '',
        }

    # origPlace
    orig_place_el = obj.find(f'.//{{{TEI_NS}}}origPlace')
    orig_place = orig_place_el.find(
        f'{{{TEI_NS}}}placeName') if orig_place_el is not None else None
    orig_place_text = orig_place.text.strip() if (
        orig_place is not None and orig_place.text) else ''

    # attestations
    attestations = []
    for bibl in obj.findall(
            f'.//{{{TEI_NS}}}listBibl[@type="attestations"]/{{{TEI_NS}}}bibl'):
        att = {'work_id': bibl.get('corresp', '')}
        t = bibl.find(f'{{{TEI_NS}}}title')
        att['title'] = t.text.strip() if t is not None and t.text else ''
        n = bibl.find(f'{{{TEI_NS}}}note')
        att['note']  = n.text.strip() if n is not None and n.text else ''
        attestations.append(att)

    # rubbings
    rubbings = []
    for b in obj.findall(
            f'.//{{{TEI_NS}}}surrogates/{{{TEI_NS}}}bibl[@type="rubbing"]'):
        ref = b.find(f'{{{TEI_NS}}}ref')
        title = b.find(f'{{{TEI_NS}}}title')
        if ref is not None:
            rubbings.append({
                'label': ref.text.strip() if ref.text else '',
                'url':   ref.get('target', ''),
            })
        elif title is not None:
            rubbings.append({'label': title.text or '', 'url': ''})

    # notes
    notes = []
    for n in obj.findall(f'{{{TEI_NS}}}note'):
        notes.append({
            'type': n.get('type', ''),
            'lang': n.get(f'{{{XML_NS}}}lang', ''),
            'text': n.text.strip() if n.text else '',
        })

    # corpus_id from idno[@type='corpus']
    corpus_id = next(
        (i['text'] for i in idnos if i['type'] == 'corpus'), '')

    return {
        'id':           xml_id,
        'vault_stem':   '',  # not vault-derived
        'name_zh':      next((n['text'] for n in names
                              if n['type'] == 'main'), ''),
        'alt_names':    [n['text'] for n in names if n['type'] == 'alt'],
        'sort_name':    next((n['text'] for n in names
                              if n['type'] == 'sort'), ''),
        'orig_when':    orig_date.get('when', ''),
        'orig_date_text': orig_date.get('text', ''),
        'orig_date_method': orig_date.get('method', ''),
        'orig_date_cert': orig_date.get('cert', ''),
        'orig_place':   orig_place_text,
        'dynasty':      '',
        'date_label':   '',
        'attestations': [
            {'work_id': a['work_id'], 'work_link': '',
             'title': a['title'], 'rest': a.get('note', ''), 'juan': ''}
            for a in attestations
        ],
        'rubbings':     rubbings,
        'corpus_id':    corpus_id,
        'extra_notes':  notes,
    }


# ── XML generators ────────────────────────────────────────────────────────────

def _i(depth):
    return INDENT * depth


def _work_xml(work, depth=3):
    """Return list of XML lines for a <bibl type='work'> element."""
    d  = _i(depth)
    d1 = _i(depth + 1)
    d2 = _i(depth + 2)
    lines = [f'{d}<bibl xml:id="{work["id"]}" type="work">']
    lines.append(f'{d1}<title xml:lang="zh">{xe(work["title_zh"])}</title>')
    if work.get('title_pinyin'):
        lines.append(
            f'{d1}<title xml:lang="zh-Latn-x-pinyin">'
            f'{xe(work["title_pinyin"])}</title>')
    if work.get('author_zh'):
        ca = (f' corresp="{work["author_id"]}"'
              if work.get('author_id') else '')
        lines.append(
            f'{d1}<author>'
            f'<persName{ca} xml:lang="zh">{xe(work["author_zh"])}</persName>'
            f'</author>')
    if work.get('year_when'):
        yw = work['year_when']
        cert = work.get('year_cert') or 'medium'
        lbl  = work.get('year_label') or str(yw)
        if isinstance(yw, int):
            lines.append(
                f'{d1}<date type="compiled" when="{yw}" cert="{cert}">'
                f'{xe(lbl)}</date>')
        elif isinstance(yw, tuple):
            nb, na = yw
            lines.append(
                f'{d1}<date type="compiled" notBefore="{nb}" notAfter="{na}"'
                f' cert="{cert}">{xe(lbl)}</date>')
    if work.get('juan'):
        lines.append(f'{d1}<extent unit="juan">{work["juan"]}</extent>')
    for i, ed in enumerate(work.get('editions', []), 1):
        ed_id = f'{work["id"]}-ed-{i:02d}'
        lines.append(f'{d1}<bibl type="edition" xml:id="{ed_id}">')
        if ed.get('label'):
            lbl = ed['label'].split('/')[-1].strip()
            lines.append(f'{d2}<edition xml:lang="zh">{xe(lbl)}</edition>')
        if ed.get('year'):
            lines.append(f'{d2}<date when="{ed["year"]}">{ed["year"]}</date>')
        if ed.get('publisher'):
            lines.append(
                f'{d2}<publisher xml:lang="zh">{xe(ed["publisher"])}</publisher>')
        if ed.get('in_collection'):
            lines.append(
                f'{d2}<note type="in-collection" xml:lang="zh">'
                f'{xe(ed["in_collection"])}</note>')
        lines.append(f'{d1}</bibl>')
    for rel in work.get('relations', []):
        if rel.get('target_id'):
            lines.append(
                f'{d1}<relatedItem type="{rel["type"]}"'
                f' target="{rel["target_id"]}"/>')
    if work.get('vault_stem'):
        lines.append(
            f'{d1}<note type="source">vault: {xe(work["vault_stem"])}</note>')
    lines.append(f'{d}</bibl>')
    return lines


def _object_xml(insc, depth=3):
    """Return list of XML lines for an <object> element."""
    d   = _i(depth)
    d1  = _i(depth + 1)
    d2  = _i(depth + 2)
    d3  = _i(depth + 3)
    d4  = _i(depth + 4)
    d5  = _i(depth + 5)

    lines = [f'{d}<object xml:id="{insc["id"]}">']
    lines.append(f'{d1}<objectIdentifier>')
    lines.append(
        f'{d2}<objectName type="main" xml:lang="zh">'
        f'{xe(insc["name_zh"])}</objectName>')
    if insc.get('sort_name'):
        lines.append(
            f'{d2}<objectName type="sort" xml:lang="zh-Latn-x-pinyin">'
            f'{xe(insc["sort_name"])}</objectName>')
    for alt in insc.get('alt_names', []):
        if alt:
            lines.append(
                f'{d2}<objectName type="alt" xml:lang="zh">'
                f'{xe(alt)}</objectName>')
    if insc.get('corpus_id'):
        lines.append(
            f'{d2}<idno type="corpus">{xe(insc["corpus_id"])}</idno>')
    lines.append(f'{d1}</objectIdentifier>')

    # History/origin
    has_date  = insc.get('orig_when') or insc.get('orig_date_text')
    has_place = insc.get('orig_place')
    if has_date or has_place:
        lines.append(f'{d1}<history>')
        lines.append(f'{d2}<origin>')
        if has_date:
            when = insc.get('orig_when', '')
            cert = insc.get('orig_date_cert', '')
            meth = insc.get('orig_date_method', 'sino:nianhao')
            txt  = insc.get('orig_date_text', '') or insc.get('date_label', '')
            attrs = f' when="{when}"' if when else ''
            attrs += f' datingMethod="{meth}"' if meth else ''
            attrs += f' cert="{cert}"' if cert else ''
            lines.append(f'{d3}<origDate{attrs}>{xe(txt)}</origDate>')
        if has_place:
            lines.append(f'{d3}<origPlace>'
                         f'<placeName xml:lang="zh">{xe(insc["orig_place"])}'
                         f'</placeName></origPlace>')
        lines.append(f'{d2}</origin>')
        lines.append(f'{d1}</history>')

    # Attestations + rubbings
    has_atts    = bool(insc.get('attestations'))
    has_rubbings = bool(insc.get('rubbings'))
    if has_atts or has_rubbings:
        lines.append(f'{d1}<additional>')
        if has_rubbings:
            lines.append(f'{d2}<surrogates>')
            for rub in insc['rubbings']:
                lines.append(f'{d3}<bibl type="rubbing">')
                if rub.get('label'):
                    lines.append(
                        f'{d4}<title xml:lang="zh">{xe(rub["label"])}</title>')
                if rub.get('url'):
                    lines.append(f'{d4}<ref target="{xe(rub["url"])}">'
                                 f'{xe(rub.get("label", ""))}</ref>')
                lines.append(f'{d3}</bibl>')
            lines.append(f'{d2}</surrogates>')
        if has_atts:
            lines.append(f'{d2}<listBibl type="attestations">')
            for att in insc['attestations']:
                wid = att.get('work_id', '')
                corresp = f' corresp="{wid}"' if wid else ''
                lines.append(f'{d3}<bibl{corresp}>')
                if att.get('title'):
                    lines.append(
                        f'{d4}<title type="title-in-work" xml:lang="zh">'
                        f'{xe(att["title"])}</title>')
                if att.get('juan'):
                    lines.append(
                        f'{d4}<citedRange unit="juan">'
                        f'{xe(att["juan"])}</citedRange>')
                note_text = att.get('rest', '') or att.get('note', '')
                if note_text:
                    lines.append(
                        f'{d4}<note xml:lang="zh">'
                        f'{xe(note_text[:200])}</note>')
                if not wid and att.get('work_link'):
                    lines.append(
                        f'{d4}<note type="source">'
                        f'{xe(att["work_link"])}</note>')
                lines.append(f'{d3}</bibl>')
            lines.append(f'{d2}</listBibl>')
        lines.append(f'{d1}</additional>')

    # Extra notes from preserved objects
    for n in insc.get('extra_notes', []):
        if n.get('text'):
            t    = f' type="{n["type"]}"' if n.get('type') else ''
            lang = f' xml:lang="{n["lang"]}"' if n.get('lang') else ''
            lines.append(f'{d1}<note{t}{lang}>{xe(n["text"])}</note>')

    if insc.get('vault_stem'):
        lines.append(
            f'{d1}<note type="source">vault: {xe(insc["vault_stem"])}</note>')

    lines.append(f'{d}</object>')
    return lines


# ── Write register XML files ──────────────────────────────────────────────────

_WORKS_HEADER = '''\
<?xml version="1.0" encoding="UTF-8"?>
<TEI xmlns="http://www.tei-c.org/ns/1.0" xml:id="pb-works">
    <teiHeader>
        <fileDesc>
            <titleStmt><title>EpiWen register: jinshi works 金石著作</title></titleStmt>
            <publicationStmt><p>Authority register for works of the epigraphic literature.
                Entry shape: doc/sino-model.md §10. Relations are stored outbound only
                (supplements/corrects/recompiles/models-on); inbound lists are derived.</p></publicationStmt>
            <sourceDesc><p>Hand seeds (M-J1); bulk entries generated by scripts/import-jinshi.py
                from the history-of-epigraphic-studies vault project.</p></sourceDesc>
        </fileDesc>
    </teiHeader>
    <standOff>
        <listBibl>'''

_WORKS_FOOTER = '''\
        </listBibl>
    </standOff>
</TEI>'''

_JINSHI_HEADER = '''\
<?xml version="1.0" encoding="UTF-8"?>
<TEI xmlns="http://www.tei-c.org/ns/1.0" xml:id="pb-jinshi">
    <teiHeader>
        <fileDesc>
            <titleStmt><title>EpiWen register: inscription authority 石刻總目</title></titleStmt>
            <publicationStmt><p>Authority register of known inscriptions with their attestation
                history (著錄) across the epigraphic literature. Entry shape: doc/sino-model.md §10.
                Attestations live here (single source of truth); a work's list of recorded
                inscriptions is derived by join.</p></publicationStmt>
            <sourceDesc><p>Hand seeds (M-J1); bulk entries generated by scripts/import-jinshi.py
                from the history-of-epigraphic-studies vault project.</p></sourceDesc>
        </fileDesc>
    </teiHeader>
    <standOff>
        <listObject>'''

_JINSHI_FOOTER = '''\
        </listObject>
    </standOff>
</TEI>'''


def write_works_xml(works, path):
    lines = [_WORKS_HEADER]
    for w in sorted(works, key=lambda x: x['id']):
        lines.extend(_work_xml(w))
    lines.append(_WORKS_FOOTER)
    Path(path).write_text('\n'.join(lines) + '\n', encoding='utf-8')


def write_jinshi_xml(inscriptions, preserved, path):
    all_insc = list(inscriptions) + list(preserved)
    lines = [_JINSHI_HEADER]
    for ins in sorted(all_insc, key=lambda x: x['id']):
        lines.extend(_object_xml(ins))
    lines.append(_JINSHI_FOOTER)
    Path(path).write_text('\n'.join(lines) + '\n', encoding='utf-8')


# ── Merge persons.xml ─────────────────────────────────────────────────────────

def load_existing_person_map(persons_path):
    """Return {zh_name: person_id} from existing persons.xml."""
    p = Path(persons_path)
    if not p.exists():
        return {}
    try:
        ET.register_namespace('', TEI_NS)
        tree = ET.parse(p)
        root = tree.getroot()
        result = {}
        for person in root.findall(f'.//{{{TEI_NS}}}person'):
            pid = _xml_id(person)
            for pn in person.findall(f'{{{TEI_NS}}}persName'):
                lang = pn.get(f'{{{XML_NS}}}lang', '')
                if lang == 'zh' and pn.text:
                    result[pn.text.strip()] = pid
        return result
    except Exception:
        return {}


def merge_persons_xml(vault_persons, existing_path, nianhao):
    """
    Merge vault persons into persons.xml:
    - For existing entries (matched by zh name): add missing birth/death/floruit.
    - For vault persons with dates not already present: add a new <person> element.
    Write back in-place.
    """
    p = Path(existing_path)
    if not p.exists():
        return

    ET.register_namespace('', TEI_NS)
    try:
        tree = ET.parse(p)
    except ET.ParseError:
        return

    root = tree.getroot()
    # Find the listPerson container
    list_person = root.find(f'.//{{{TEI_NS}}}listPerson')
    if list_person is None:
        return

    # Build zh→person element map
    person_els = {}
    existing_ids = set()
    for el in list_person.findall(f'{{{TEI_NS}}}person'):
        existing_ids.add(el.get(f'{{{XML_NS}}}id', ''))
        for pn in el.findall(f'{{{TEI_NS}}}persName'):
            if pn.get(f'{{{XML_NS}}}lang') == 'zh' and pn.text:
                person_els[pn.text.strip()] = el

    modified = False
    for vp in vault_persons:
        zh    = vp.get('zh', '')
        dates = vp.get('dates', {})
        if not zh:
            continue
        # Need at least one datable anchor to be useful on the timeline
        has_date = (dates.get('birth') or dates.get('death')
                    or dates.get('floruit_from'))
        el = person_els.get(zh)

        if el is not None:
            # Patch missing date elements onto existing entry
            has_birth   = el.find(f'{{{TEI_NS}}}birth')   is not None
            has_death   = el.find(f'{{{TEI_NS}}}death')   is not None
            has_floruit = el.find(f'{{{TEI_NS}}}floruit') is not None
            if not has_birth and dates.get('birth'):
                b = ET.SubElement(el, f'{{{TEI_NS}}}birth')
                b.set('when', str(dates['birth']))
                modified = True
            if not has_death and dates.get('death'):
                d = ET.SubElement(el, f'{{{TEI_NS}}}death')
                d.set('when', str(dates['death']))
                modified = True
            if not has_floruit and dates.get('floruit_from'):
                f_el = ET.SubElement(el, f'{{{TEI_NS}}}floruit')
                f_el.set('notBefore', str(dates['floruit_from']))
                f_el.set('notAfter',  str(dates.get('floruit_to', dates['floruit_from'])))
                f_el.set('cert', dates.get('cert', 'low'))
                if dates.get('literal'):
                    f_el.text = dates['literal']
                modified = True
        elif has_date:
            # New person with dates — add a minimal entry for the timeline
            pid = vp.get('id', '')
            if not pid or pid in existing_ids:
                continue
            new_el = ET.SubElement(list_person, f'{{{TEI_NS}}}person')
            new_el.set(f'{{{XML_NS}}}id', pid)
            cn = ET.SubElement(new_el, f'{{{TEI_NS}}}persName')
            cn.set('type', 'canonical')
            cn.set(f'{{{XML_NS}}}lang', 'zh')
            cn.text = zh
            pinyin = vp.get('pinyin', '')
            if pinyin:
                py = ET.SubElement(new_el, f'{{{TEI_NS}}}persName')
                py.set(f'{{{XML_NS}}}lang', 'zh-Latn-pinyin')
                py.text = pinyin
            if dates.get('birth'):
                b = ET.SubElement(new_el, f'{{{TEI_NS}}}birth')
                b.set('when', str(dates['birth']))
            if dates.get('death'):
                d = ET.SubElement(new_el, f'{{{TEI_NS}}}death')
                d.set('when', str(dates['death']))
            if dates.get('floruit_from'):
                f_el = ET.SubElement(new_el, f'{{{TEI_NS}}}floruit')
                f_el.set('notBefore', str(dates['floruit_from']))
                f_el.set('notAfter',  str(dates.get('floruit_to', dates['floruit_from'])))
                f_el.set('cert', dates.get('cert', 'low'))
                if dates.get('literal'):
                    f_el.text = dates['literal']
            existing_ids.add(pid)
            person_els[zh] = new_el
            modified = True

    if modified:
        tree.write(str(p), encoding='unicode', xml_declaration=True,
                   default_namespace=None)


# ── Report generator ──────────────────────────────────────────────────────────

def write_report(work_stats, insc_stats, person_stats,
                 insc_list, path, dry_run):
    total   = insc_stats.get('att_total', 0)
    parsed  = insc_stats.get('att_parsed', 0)
    rate    = (parsed / total * 100) if total else 0
    unparsed = insc_stats.get('unparsed', [])

    lines = [
        '# EpiWen — jinshi import report',
        '',
        f'*Generated by scripts/import-jinshi.py'
        f'{" (dry-run)" if dry_run else ""}*',
        '',
        '## Summary',
        '',
        f'| Category | Count |',
        f'|---|---|',
        f'| Works processed | {work_stats.get("count", 0)} |',
        f'| Works with year | {work_stats.get("with_year", 0)} |',
        f'| Works with author | {work_stats.get("with_author", 0)} |',
        f'| Inscriptions processed | {insc_stats.get("count", 0)} |',
        f'| Attestation lines total | {total} |',
        f'| Attestations parsed | {parsed} ({rate:.1f}%) |',
        f'| Persons processed | {person_stats.get("count", 0)} |',
        f'| Persons with dates | {person_stats.get("with_dates", 0)} |',
        '',
    ]

    if unparsed:
        lines += [
            '## Unparsed attestation lines',
            '',
            'Lines that did not match the attestation regex (kept as '
            '`<note type="source">`):',
            '',
        ]
        for u in unparsed[:200]:
            lines.append(f'- `{u}`')
        if len(unparsed) > 200:
            lines.append(f'- … and {len(unparsed) - 200} more')
        lines.append('')

    if work_stats.get('errors'):
        lines += ['## Work parse errors', '']
        for e in work_stats['errors'][:50]:
            lines.append(f'- `{e}`')
        lines.append('')

    Path(path).write_text('\n'.join(lines), encoding='utf-8')


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    ap = argparse.ArgumentParser(
        description='Import jinshi register data from an Obsidian vault.')
    ap.add_argument('--vault',    required=True,
                    help='Vault root directory')
    ap.add_argument('--data-pkg', default='data-pkg',
                    help='data-pkg directory (default: data-pkg)')
    ap.add_argument('--id-map',   default='scripts/jinshi-id-map.json',
                    help='ID map JSON file')
    ap.add_argument('--report',   default='scripts/jinshi-import-report.md',
                    help='Report output file')
    ap.add_argument('--dry-run',  action='store_true',
                    help='Parse only; do not write XML files')
    args = ap.parse_args()

    vault    = Path(args.vault)
    data_pkg = Path(args.data_pkg)

    if not vault.exists():
        print(f'ERROR: vault not found: {vault}', file=sys.stderr)
        sys.exit(1)

    # 1. Load id map
    id_map = load_id_map(args.id_map)

    # 2. Load nianhao for era resolution
    nianhao = load_nianhao(data_pkg)

    # 3. Build alias map (wikilink targets → vault stems)
    print('Building alias map …', file=sys.stderr)
    alias_map = build_alias_map(vault)

    # 4. Import works
    print('Importing works …', file=sys.stderr)
    works, work_stats = import_works(vault, id_map, alias_map)
    print(f'  {work_stats["count"]} works', file=sys.stderr)

    # 5. Import edition files and merge into works
    print('Importing editions …', file=sys.stderr)
    edition_files = import_edition_files(vault, id_map, alias_map)
    merge_editions(works, edition_files, alias_map)

    # 6. Import inscriptions
    print('Importing inscriptions …', file=sys.stderr)
    inscriptions, insc_stats = import_inscriptions(vault, id_map, alias_map)
    total  = insc_stats['att_total']
    parsed = insc_stats['att_parsed']
    rate   = (parsed / total * 100) if total else 0
    print(f'  {insc_stats["count"]} inscriptions, '
          f'{parsed}/{total} attestations parsed ({rate:.1f}%)',
          file=sys.stderr)

    # 7. Import persons
    print('Importing persons …', file=sys.stderr)
    vault_persons, person_stats = import_persons(
        vault, id_map, alias_map, nianhao)
    print(f'  {person_stats["count"]} persons', file=sys.stderr)

    # 8. Resolve author IDs in works against persons.xml
    persons_path   = data_pkg / 'data/registers/persons.xml'
    existing_pmap  = load_existing_person_map(persons_path)
    resolve_author_ids(works, vault_persons, existing_pmap)

    # 9. Save id map (assigns have already been made above)
    if not args.dry_run:
        save_id_map(id_map, args.id_map)

    # 10. Write works.xml
    works_path  = data_pkg / 'data/registers/works.xml'
    jinshi_path = data_pkg / 'data/registers/jinshi.xml'

    if not args.dry_run:
        # Preserve non-vault objects (e.g. insc-demo-000001)
        vault_insc_ids = {i['id'] for i in inscriptions}
        preserved      = load_preserved_objects(jinshi_path, vault_insc_ids)

        works_path.parent.mkdir(parents=True, exist_ok=True)
        write_works_xml(works, works_path)
        write_jinshi_xml(inscriptions, preserved, jinshi_path)
        merge_persons_xml(vault_persons, persons_path, nianhao)
        print(f'Wrote {works_path}', file=sys.stderr)
        print(f'Wrote {jinshi_path}', file=sys.stderr)

    # 11. Write report
    write_report(work_stats, insc_stats, person_stats,
                 inscriptions, args.report, args.dry_run)
    print(f'Wrote {args.report}', file=sys.stderr)


if __name__ == '__main__':
    main()
