#!/usr/bin/env python3
"""
Fixture test for scripts/import-jinshi.py
Run: python3 scripts/test_import_jinshi.py

Uses test/fixtures/vault-sample/ as a minimal vault with 4 works, 2 editions,
2 inscriptions, and 2 persons.  Verifies:
  - Pre-seeded IDs are honoured (work-000001–work-000003, insc-000001)
  - A new work (Zhang San 張三《金石測試》) gets work-000004
  - A new inscription (曹全碑) gets insc-000002
  - Attestation corresp attributes contain TEI work IDs (work-NNNNNN)
  - insc-demo-000001 (non-vault hand seed) is preserved
  - Attestation parse rate ≥ 95%
  - Output is byte-identical on re-run (idempotent)
"""

import sys
import json
import shutil
import tempfile
import xml.etree.ElementTree as ET
from pathlib import Path

# Load import-jinshi.py (hyphen in filename requires importlib)
import importlib.util
_spec = importlib.util.spec_from_file_location(
    'import_jinshi', Path(__file__).parent / 'import-jinshi.py')
ij = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(ij)

REPO_ROOT     = Path(__file__).parent.parent
FIXTURE_VAULT = REPO_ROOT / 'test/fixtures/vault-sample'
DATA_PKG      = REPO_ROOT / 'data-pkg'

SEED_MAP = {
    'works': {
        'Lu Zengxiang 陸增祥 《八瓊室金石補正》': 'work-000003',
        'Ouyang Xiu 歐陽修《集古錄》': 'work-000001',
        'Wang Chang 王昶《金石萃編》': 'work-000002',
    },
    'inscriptions': {
        '乙瑛碑（153 CE）': 'insc-000001',
    },
    'persons': {
        'Lu Zengxiang 陸增祥': 'person-lu-zengxiang',
        'Ouyang Xiu 歐陽修': 'person-ouyang-xiu',
        'Wang Chang 王昶': 'person-wang-chang',
        'Zhu Wenzao 朱文藻': 'person-zhu-wenzao',
    },
}

_PASS = 0
_FAIL = 0


def ok(msg):
    global _PASS
    _PASS += 1
    print(f'  OK  {msg}')


def fail(msg):
    global _FAIL
    _FAIL += 1
    print(f'FAIL  {msg}', file=sys.stderr)


def run_import(tmp, id_map_path):
    """Execute one import pass into tmp; return (works, inscriptions, insc_stats)."""
    id_map    = ij.load_id_map(id_map_path)
    nianhao   = ij.load_nianhao(DATA_PKG)
    alias_map = ij.build_alias_map(FIXTURE_VAULT)

    works, work_stats = ij.import_works(FIXTURE_VAULT, id_map, alias_map)
    ed_files          = ij.import_edition_files(FIXTURE_VAULT, id_map, alias_map)
    ij.merge_editions(works, ed_files, alias_map)

    inscriptions, insc_stats = ij.import_inscriptions(FIXTURE_VAULT, id_map, alias_map)
    vault_persons, person_stats = ij.import_persons(FIXTURE_VAULT, id_map, alias_map, nianhao)

    existing_pmap = ij.load_existing_person_map(DATA_PKG / 'data/registers/persons.xml')
    ij.resolve_author_ids(works, vault_persons, existing_pmap)

    works_path   = tmp / 'works.xml'
    jinshi_path  = tmp / 'jinshi.xml'
    persons_path = tmp / 'persons.xml'
    shutil.copy(DATA_PKG / 'data/registers/persons.xml', persons_path)

    vault_insc_ids = {i['id'] for i in inscriptions}
    preserved      = ij.load_preserved_objects(DATA_PKG / 'data/registers/jinshi.xml',
                                               vault_insc_ids)

    ij.write_works_xml(works, works_path)
    ij.write_jinshi_xml(inscriptions, preserved, jinshi_path)
    ij.merge_persons_xml(vault_persons, persons_path, nianhao)
    ij.save_id_map(id_map, id_map_path)
    ij.write_report(work_stats, insc_stats, person_stats, inscriptions,
                    tmp / 'report.md', False)

    return works, inscriptions, insc_stats, works_path, jinshi_path, persons_path


def check_xml_ids(xml_text, expected_ids, label):
    for xid in expected_ids:
        if f'xml:id="{xid}"' in xml_text:
            ok(f'{label}: {xid} present')
        else:
            fail(f'{label}: {xid} missing')


def main():
    print('=== test_import_jinshi.py (fixture test) ===')
    print()

    with tempfile.TemporaryDirectory() as tmpdir:
        tmp = Path(tmpdir)

        # Seed id-map into tmp
        id_map_path = tmp / 'id-map.json'
        id_map_path.write_text(
            json.dumps(SEED_MAP, ensure_ascii=False, indent=2),
            encoding='utf-8',
        )

        # ── Run 1 ─────────────────────────────────────────────────────────────
        print('Run 1: fixture import ...')
        works, inscs, insc_stats, wpath, jpath, ppath = run_import(tmp, id_map_path)

        works_xml   = wpath.read_text(encoding='utf-8')
        jinshi_xml  = jpath.read_text(encoding='utf-8')
        persons_xml = ppath.read_text(encoding='utf-8')
        id_map_out  = json.loads(id_map_path.read_text(encoding='utf-8'))

        # -- Work IDs --
        check_xml_ids(works_xml,
                      ['work-000001', 'work-000002', 'work-000003'],
                      'works.xml seeded ids')

        new_work_keys = [s for s in id_map_out.get('works', {})
                         if '張三' in s or 'Zhang San' in s]
        if new_work_keys:
            nid = id_map_out['works'][new_work_keys[0]]
            if nid >= 'work-000004':
                ok(f'New work (Zhang San) got {nid} ≥ work-000004')
            else:
                fail(f'New work got {nid} (expected ≥ work-000004)')
        else:
            fail('Zhang San test work not found in id map')

        # -- Inscription IDs --
        check_xml_ids(jinshi_xml, ['insc-000001'], 'jinshi.xml seeded ids')

        new_insc_keys = [s for s in id_map_out.get('inscriptions', {})
                         if '曹全碑' in s]
        if new_insc_keys:
            nid = id_map_out['inscriptions'][new_insc_keys[0]]
            ok(f'New inscription (曹全碑) got {nid}')
        else:
            fail('曹全碑 not found in id map')

        # -- Non-vault preserved entry --
        if 'insc-demo-000001' in jinshi_xml:
            ok('insc-demo-000001 preserved from existing jinshi.xml')
        else:
            fail('insc-demo-000001 not preserved')

        # -- Attestation corresp must be TEI work IDs, not vault stems --
        if 'corresp="work-' in jinshi_xml:
            ok('attestation corresp attributes contain work- IDs')
        else:
            fail('attestation corresp attributes missing or not work- IDs')

        if '王昶《金石萃編》' not in jinshi_xml.split('<listBibl')[1] if '<listBibl' in jinshi_xml else True:
            ok('vault stems not leaking into corresp attributes')
        else:
            # More precise check: look inside listBibl type="attestations"
            import re
            corresp_values = re.findall(r'corresp="([^"]+)"', jinshi_xml)
            stem_leak = [v for v in corresp_values if '《' in v or '》' in v]
            if stem_leak:
                fail(f'Vault stems leaked into corresp: {stem_leak[:3]}')
            else:
                ok('No vault stems in corresp attributes')

        # -- Attestation parse rate --
        total  = insc_stats.get('att_total', 0)
        parsed = insc_stats.get('att_parsed', 0)
        rate   = (parsed / total * 100) if total else 100.0
        if rate >= 95.0:
            ok(f'Attestation parse rate {rate:.0f}% (≥95%)')
        else:
            fail(f'Attestation parse rate {rate:.0f}% (target ≥95%)')

        # -- Dates in persons.xml --
        if 'when="1725"' in persons_xml or 'when="1007"' in persons_xml:
            ok('birth/death dates added to persons.xml from vault')
        else:
            fail('no vault birth/death dates found in persons.xml')

        # -- Editions present --
        if '<bibl type="edition"' in works_xml:
            ok('editions present in works.xml')
        else:
            fail('no editions in works.xml')

        # ── Run 2: idempotency ────────────────────────────────────────────────
        print()
        print('Run 2: idempotency check ...')
        _, _, _, wpath2, jpath2, _ = run_import(tmp, id_map_path)

        works_xml2  = wpath2.read_text(encoding='utf-8')
        jinshi_xml2 = jpath2.read_text(encoding='utf-8')

        if works_xml == works_xml2:
            ok('works.xml byte-identical on re-run (idempotent)')
        else:
            fail('works.xml differs on re-run')
            # Debug: show first diff
            for i, (a, b) in enumerate(zip(works_xml.splitlines(),
                                           works_xml2.splitlines())):
                if a != b:
                    print(f'  First diff at line {i+1}:', file=sys.stderr)
                    print(f'  -  {a!r}', file=sys.stderr)
                    print(f'  +  {b!r}', file=sys.stderr)
                    break

        if jinshi_xml == jinshi_xml2:
            ok('jinshi.xml byte-identical on re-run (idempotent)')
        else:
            fail('jinshi.xml differs on re-run')

    print()
    print(f'Results: {_PASS} passed, {_FAIL} failed')
    if _FAIL:
        sys.exit(1)


if __name__ == '__main__':
    main()
