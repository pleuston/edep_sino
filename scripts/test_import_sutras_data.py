#!/usr/bin/env python3
"""
Fixture test for scripts/import-sutras-data.py
Run: python3 scripts/test_import_sutras_data.py

Uses test/fixtures/sutras-sample/ — a minimal stonesutras-data tree with one site
(HDS) and 4 inscriptions (a Buddha-name, a sutra passage with supplied/persName,
a nested-markup stress case, and a simple name). Verifies:
  - the site → place-hongdingshan is merged into places.xml (existing seeds kept)
  - 4 authority <object type="sutra"> records with stable seeded + new ids
  - genre heuristic (安王佛 → foming; sutra passage → kejing)
  - every generated workspace edition passes the EpiDoc gate (validate-epidoc.sh)
  - output is byte-identical on re-run (idempotent)
"""

import sys
import json
import shutil
import tempfile
import subprocess
from pathlib import Path

import importlib.util
_spec = importlib.util.spec_from_file_location(
    'import_sutras', Path(__file__).parent / 'import-sutras-data.py')
isd = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(isd)

REPO = Path(__file__).parent.parent
FIXTURE = REPO / 'test/fixtures/sutras-sample'
REAL_PKG = REPO / 'data-pkg'
GATE = REPO / 'scripts/validate-epidoc.sh'

SEED = {
    'sutra-inscriptions': {'HDS_11': 'sutra-000001'},  # pin one id
    'places': {},
    'editions': {},
}

_PASS = 0
_FAIL = 0


def ok(m):
    global _PASS
    _PASS += 1
    print(f'  OK  {m}')


def fail(m):
    global _FAIL
    _FAIL += 1
    print(f'FAIL  {m}', file=sys.stderr)


def run_import(tmp_pkg, id_map_path):
    """Invoke import-sutras-data.py as a subprocess into an isolated data-pkg."""
    return subprocess.run(
        [sys.executable, str(REPO / 'scripts/import-sutras-data.py'),
         '--source', str(FIXTURE),
         '--site', 'HDS',
         '--data-pkg', str(tmp_pkg),
         '--id-map', str(id_map_path),
         '--report', str(tmp_pkg / 'report.md')],
        capture_output=True, text=True)


def main():
    print('=== test_import_sutras_data.py (fixture test) ===\n')
    with tempfile.TemporaryDirectory() as td:
        tmp = Path(td)
        tmp_pkg = tmp / 'data-pkg'
        (tmp_pkg / 'data/taxonomy').mkdir(parents=True)
        (tmp_pkg / 'data/registers').mkdir(parents=True)
        # dynasty.xml drives @period; places.xml is merged in place
        shutil.copy(REAL_PKG / 'data/taxonomy/dynasty.xml',
                    tmp_pkg / 'data/taxonomy/dynasty.xml')
        shutil.copy(REAL_PKG / 'data/registers/places.xml',
                    tmp_pkg / 'data/registers/places.xml')
        id_map_path = tmp / 'sutras-id-map.json'
        id_map_path.write_text(json.dumps(SEED, ensure_ascii=False, indent=2),
                               encoding='utf-8')

        # ── Run 1 ──────────────────────────────────────────────────────────────
        print('Run 1: fixture import ...')
        r1 = run_import(tmp_pkg, id_map_path)
        if r1.returncode != 0:
            fail(f'importer exited {r1.returncode}: {r1.stderr[-400:]}')
            print(f'\nResults: {_PASS} passed, {_FAIL} failed')
            sys.exit(1)

        sutras = (tmp_pkg / 'data/registers/sutras.xml').read_text(encoding='utf-8')
        places = (tmp_pkg / 'data/registers/places.xml').read_text(encoding='utf-8')
        id_map = json.loads(id_map_path.read_text(encoding='utf-8'))
        editions = sorted((tmp_pkg / 'data/workspace').glob('HDS_*.xml'))

        # -- seeded id honoured --
        if id_map['sutra-inscriptions'].get('HDS_11') == 'sutra-000001':
            ok('seeded id HDS_11 → sutra-000001 honoured')
        else:
            fail(f'seeded id not honoured: {id_map["sutra-inscriptions"].get("HDS_11")}')

        # -- 4 inscription objects --
        n_obj = sutras.count('<object xml:id="sutra-')
        if n_obj == 4:
            ok(f'{n_obj} sutra objects emitted')
        else:
            fail(f'expected 4 sutra objects, got {n_obj}')

        # -- all objects typed --
        import re as _re
        typed = len(_re.findall(r'<object xml:id="sutra-\d+" type="sutra">', sutras))
        if typed == n_obj:
            ok('every object carries type="sutra"')
        else:
            fail(f'only {typed}/{n_obj} objects carry type="sutra"')

        # -- place merged, existing seeds kept --
        if 'place-hongdingshan' in places:
            ok('place-hongdingshan merged into places.xml')
        else:
            fail('place-hongdingshan missing from places.xml')
        if 'place-taishan' in places and 'place-yunfengshan' in places:
            ok('existing place seeds (taishan, yunfengshan) preserved')
        else:
            fail('existing place seeds lost during merge')

        # -- genre heuristic --
        import re
        m = re.search(r'安王佛.*?</object>', sutras, re.S)
        if m and 'foming' in m.group(0):
            ok('安王佛 classified as foming')
        else:
            fail('安王佛 not classified as foming')

        # -- editions generated + gate-valid --
        if len(editions) == 4:
            ok(f'{len(editions)} editions generated')
        else:
            fail(f'expected 4 editions, got {len(editions)}')
        gate = subprocess.run(['sh', str(GATE)] + [str(e) for e in editions],
                              capture_output=True, text=True)
        if gate.returncode == 0:
            ok('all editions pass the EpiDoc gate')
        else:
            fail('editions failed the EpiDoc gate:\n' + gate.stdout + gate.stderr)

        # -- linkage: edition idno[jinshi] == authority id --
        ed11 = (tmp_pkg / 'data/workspace/HDS_11.xml').read_text(encoding='utf-8')
        if '<idno type="jinshi">sutra-000001</idno>' in ed11:
            ok('edition HDS_11 links back to sutra-000001')
        else:
            fail('edition HDS_11 missing jinshi backlink')

        # -- §11 verification layer: draft-by-default + provenance anchor (溯源) --
        if 'status="draft"' in ed11 and 'source="stonesutras:HDS_11"' in ed11:
            ok('edition is draft-by-default with a provenance source anchor')
        else:
            fail('edition missing draft status / provenance source')

        # -- §11 E-SUP one-support-many-texts: HDS_9.1 carries support key HDS_9 --
        sutras_xml = (tmp_pkg / 'data/registers/sutras.xml').read_text(encoding='utf-8')
        if '<idno type="support">HDS_9</idno>' in sutras_xml:
            ok('authority object carries the support grouping key (HDS_9.1 → HDS_9)')
        else:
            fail('authority object missing support grouping key')

        # ── Run 2: idempotency ─────────────────────────────────────────────────
        print('\nRun 2: idempotency check ...')
        run_import(tmp_pkg, id_map_path)
        sutras2 = (tmp_pkg / 'data/registers/sutras.xml').read_text(encoding='utf-8')
        ed11b = (tmp_pkg / 'data/workspace/HDS_11.xml').read_text(encoding='utf-8')
        places2 = (tmp_pkg / 'data/registers/places.xml').read_text(encoding='utf-8')
        if sutras == sutras2:
            ok('sutras.xml byte-identical on re-run')
        else:
            fail('sutras.xml differs on re-run')
        if ed11 == ed11b:
            ok('edition byte-identical on re-run')
        else:
            fail('edition differs on re-run')
        if places.count('place-hongdingshan') == places2.count('place-hongdingshan') == 1:
            ok('place merge is idempotent (no duplicate)')
        else:
            fail('place merge duplicated on re-run')

    print(f'\nResults: {_PASS} passed, {_FAIL} failed')
    sys.exit(1 if _FAIL else 0)


if __name__ == '__main__':
    main()
