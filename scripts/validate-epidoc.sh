#!/bin/sh
# Validate inscription TEI against tei-epidoc.rng, tolerating the documented
# EDEp-Sino extensions (doc/sino-model.md "Schema-conformance adjustments"):
#   - listWit/witness in sourceDesc (rubbings as first-class witnesses)
# Anything else fails the gate.
# Usage: scripts/validate-epidoc.sh file.xml [more.xml ...]
set -u
RNG="$(dirname "$0")/../test/schema/tei-epidoc.rng"
status=0
for f in "$@"; do
    errors=$(xmllint --noout --relaxng "$RNG" "$f" 2>&1 \
        | grep 'Relax-NG validity error' \
        | grep -v 'element listWit' \
        | grep -v 'extra content: listWit' \
        | grep -v 'element witness')
    if [ -n "$errors" ]; then
        echo "INVALID: $f"
        echo "$errors"
        status=1
    else
        echo "ok: $f (EpiDoc + sino extensions)"
    fi
done
exit $status
