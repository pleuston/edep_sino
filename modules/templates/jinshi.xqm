xquery version "3.1";

(:~
 : EpiWen — joins for the jinshi history layer (doc/sino-model.md par.10):
 : works register 金石著作 (pb-works) ↔ inscription authority register
 : 石刻總目 (pb-jinshi) ↔ persons ↔ corpus documents.
 :
 : Attestations are stored once, on the inscription authority record
 : (object/additional/listBibl[@type='attestations']/bibl/@corresp = work id);
 : everything else here is derived from that single source of truth.
 :)
module namespace jinshi="http://epiwen.org/templates/jinshi";

import module namespace config="http://www.tei-c.org/tei-simple/config" at "../config.xqm";

declare namespace tei="http://www.tei-c.org/ns/1.0";

declare %private function jinshi:works-root() {
    collection($config:register-root)/id($config:register-map?work?id)
};

declare %private function jinshi:objects-root() {
    collection($config:register-root)/id($config:register-map?inscription?id)
};

(:~ Numeric sort key for a work: year of compilation (or start of range), else 9999. :)
declare %private function jinshi:work-year($work as element()?) as xs:integer {
    let $date := $work/tei:date[@type = 'compiled']
    let $raw := head(($date/@when, $date/@notBefore, $date/@notAfter))
    let $year := replace($raw, '^(-?\d{1,4}).*$', '$1')
    return
        if ($year castable as xs:integer) then xs:integer($year) else 9999
};

declare %private function jinshi:work-summary($work as element()) as map(*) {
    map {
        "id": $work/@xml:id/string(),
        "title": head(($work/tei:title[@xml:lang = 'zh'], $work/tei:title))/string(),
        "sort-title": head(($work/tei:title[@xml:lang = 'zh-Latn-x-pinyin'], $work/tei:title[@type = 'sort'], $work/tei:title))/string(),
        "author": head(($work/tei:author/tei:persName, $work/tei:author))/string(),
        "author-id": $work/tei:author/tei:persName/@corresp/string(),
        "date": $work/tei:date[@type = 'compiled']/string(),
        "year": jinshi:work-year($work),
        "juan": $work/tei:extent[@unit = 'juan']/string()
    }
};

declare %private function jinshi:object-summary($object as element()) as map(*) {
    map {
        "id": $object/@xml:id/string(),
        "name": head(($object//tei:objectName[@type = 'main'], $object//tei:objectName))/string(),
        "sort-name": ($object//tei:objectName[@type = 'sort']/string(), '')[1],
        "date": ($object//tei:origin/tei:origDate/string(), '')[1],
        "when": ($object//tei:origin/tei:origDate/@when/string(), '')[1],
        "place": ($object//tei:origin/tei:origPlace/string(), '')[1]
    }
};

(:~ Works authored (or co-produced) by the given person, oldest first.
 : Used by templates/person.html. :)
declare function jinshi:works-of-person($id as xs:string?) as map(*)* {
    if (empty($id) or $id = '') then () else
    let $works := jinshi:works-root()
        //tei:bibl[@type = 'work'][.//tei:persName/@corresp = $id]
    for $work in $works
    let $role :=
        if ($work/tei:author/tei:persName/@corresp = $id) then 'author' else 'contributor'
    order by jinshi:work-year($work), $work/@xml:id
    return
        map:merge((jinshi:work-summary($work), map { "role": $role }))
};

(:~ Inscriptions recorded in the given work — derived from the attestations
 : stored on the authority records. Used by templates/work.html. :)
declare function jinshi:inscriptions-in-work($work-id as xs:string?) as map(*)* {
    if (empty($work-id) or $work-id = '') then () else
    let $objects := jinshi:objects-root()
        //tei:object[tei:additional/tei:listBibl[@type = 'attestations']/tei:bibl/@corresp = $work-id]
    for $object in $objects
    let $att := $object/tei:additional/tei:listBibl[@type = 'attestations']/tei:bibl[@corresp = $work-id][1]
    order by ($object//tei:origin/tei:origDate/@when/string(), '9999')[1]
    return
        map:merge((jinshi:object-summary($object), map {
            "title-in-work": ($att/tei:title[@type = 'title-in-work']/string(), '')[1],
            "juan": ($att/tei:citedRange[@unit = 'juan']/string(), '')[1]
        }))
};

(:~ The attestation history of an inscription authority record: each recording
 : work, ordered by the work's compilation date — the reception timeline.
 : Used by templates/jinshi-inscription.html. :)
declare function jinshi:attestations-of($insc-id as xs:string?) as map(*)* {
    if (empty($insc-id) or $insc-id = '') then () else
    let $object := jinshi:objects-root()//tei:object[@xml:id = $insc-id]
    for $att in $object/tei:additional/tei:listBibl[@type = 'attestations']/tei:bibl
    let $work := jinshi:works-root()//tei:bibl[@type = 'work'][@xml:id = $att/@corresp]
    let $year := if ($work) then jinshi:work-year($work) else 9999
    order by $year, $att/@corresp
    return
        map {
            "work-id": $att/@corresp/string(),
            "work-title": if ($work) then head(($work/tei:title[@xml:lang = 'zh'], $work/tei:title))/string() else $att/@corresp/string(),
            "work-author": ($work/tei:author/tei:persName/string(), '')[1],
            "work-date": ($work/tei:date[@type = 'compiled']/string(), '')[1],
            "year": $year,
            "title-in-work": ($att/tei:title[@type = 'title-in-work']/string(), '')[1],
            "juan": ($att/tei:citedRange[@unit = 'juan']/string(), '')[1],
            "note": ($att/tei:note/string(), '')[1]
        }
};

(:~ Typed relations of a work: stored outbound links plus derived inbound ones
 : (voice inversion — "supplemented-by" is never stored). Labels are i18n keys
 : jinshi.rel.<type> / jinshi.rel.<type>-by. :)
declare function jinshi:relations-of($work-id as xs:string?) as map(*)* {
    if (empty($work-id) or $work-id = '') then () else
    let $works := jinshi:works-root()
    let $work := $works//tei:bibl[@type = 'work'][@xml:id = $work-id]
    let $outbound :=
        for $rel in $work/tei:relatedItem[@target]
        let $target := $works//tei:bibl[@type = 'work'][@xml:id = $rel/@target]
        return
            map {
                "dir": "out",
                "type": $rel/@type/string(),
                "label-key": "jinshi.rel." || $rel/@type,
                "id": $rel/@target/string(),
                "title": if ($target) then head(($target/tei:title[@xml:lang = 'zh'], $target/tei:title))/string() else $rel/@target/string()
            }
    let $inbound :=
        for $other in $works//tei:bibl[@type = 'work'][tei:relatedItem/@target = $work-id]
        for $rel in $other/tei:relatedItem[@target = $work-id]
        return
            map {
                "dir": "in",
                "type": $rel/@type/string(),
                "label-key": "jinshi.rel." || $rel/@type || "-by",
                "id": $other/@xml:id/string(),
                "title": head(($other/tei:title[@xml:lang = 'zh'], $other/tei:title))/string()
            }
    return ($outbound, $inbound)
};

(:~ The corpus document (our EpiDoc edition) paired with an authority record,
 : via object//idno[@type='corpus'] = the document's EDEp idno. :)
declare function jinshi:corpus-doc-for($insc-id as xs:string?) as map(*)* {
    if (empty($insc-id) or $insc-id = '') then () else
    let $corpus-id := jinshi:objects-root()
        //tei:object[@xml:id = $insc-id]//tei:idno[@type = 'corpus']/string()
    where $corpus-id != ''
    for $tei in collection($config:inscription)//tei:idno[@type = 'EDEp'][. = $corpus-id]/ancestor::tei:TEI
    return
        map {
            "file": util:document-name(root($tei)),
            "id": $corpus-id,
            "title": string-join($tei//tei:titleStmt/tei:title//text(), '')
        }
};

(:~ The authority record paired with a corpus document (by the document's
 : idno type="jinshi"), with its attestation count. Used on the document view;
 : $path is the document path as found in $context?doc?path. :)
declare function jinshi:authority-for-corpus-doc($path as xs:string?) as map(*)* {
    let $doc := if (exists($path) and $path != '') then config:get-document($path) else ()
    let $insc-id := normalize-space(($doc//tei:msIdentifier/tei:idno[@type = 'jinshi'])[1])
    where $insc-id != ''
    let $object := jinshi:objects-root()//tei:object[@xml:id = $insc-id]
    where $object
    return
        map:merge((jinshi:object-summary($object), map {
            "attestations": count($object/tei:additional/tei:listBibl[@type = 'attestations']/tei:bibl)
        }))
};
