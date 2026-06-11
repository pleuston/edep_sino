xquery version "3.1";

(:~
 : EpiWen — the "site" navigation axis: find-spots joined with the
 : inscriptions found there (origPlace/@corresp -> place entity files).
 : Used by templates/map.html, templates/sites.html and /api/sites.
 :)
module namespace sites="http://epiwen.org/templates/sites";

import module namespace config="http://www.tei-c.org/tei-simple/config" at "../config.xqm";

declare namespace tei="http://www.tei-c.org/ns/1.0";

declare %private function sites:label($taxonomy as xs:string, $curie as xs:string?) as xs:string? {
    if ($curie) then
        doc($config:data-root || "/taxonomy/" || $taxonomy || ".xml")
            //tei:category[@corresp = $curie]/tei:catDesc[@xml:lang = 'zh']/string()
    else ()
};

declare %private function sites:inscription($tei as element(tei:TEI)) as map(*) {
    map {
        "file": util:document-name(root($tei)),
        "id": $tei//tei:idno[@type = 'EDEp']/string(),
        "title": string-join($tei//tei:titleStmt/tei:title//text(), ''),
        "period": (sites:label('dynasty', $tei//tei:origin/tei:origDate/@period/string()), '')[1],
        "objtype": (sites:label('objtyp', $tei//tei:objectType/@ref/string()), '')[1]
    }
};

(:~ All sites (place entity files), each with its inscriptions; sites with
 : holdings first, by count descending. :)
declare function sites:all($context as map(*)?) as map(*)* {
    let $entries :=
        for $place in collection($config:places)//tei:place
        let $id := $place/@xml:id/string()
        let $texts :=
            for $t in collection($config:inscription)//tei:TEI[.//tei:origPlace/@corresp = $id]
            return sites:inscription($t)
        let $geo := tokenize(normalize-space($place/tei:location/tei:geo), '\s+')
        order by count($texts) descending, $id
        return
            map {
                "id": $id,
                "name": head(($place/tei:placeName[@type = 'findspot'], $place/tei:placeName[@type = 'main'], $place/tei:placeName))/string(),
                "pinyin": ($place/tei:placeName[@type = 'sort']/string(), '')[1],
                "region": ($place/tei:region[@type = 'modern']/string(), $place/tei:region[1]/string(), '')[1],
                "lat": $geo[1],
                "lng": $geo[2],
                "count": count($texts),
                "inscriptions": array { $texts }
            }
    return $entries
};

(:~ Inscriptions at one site, for the place detail page. :)
declare function sites:inscriptions-at($id as xs:string) as map(*)* {
    for $t in collection($config:inscription)//tei:TEI[.//tei:origPlace/@corresp = $id]
    return sites:inscription($t)
};
