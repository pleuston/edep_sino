xquery version "3.1";

module namespace rview="http://teipublisher.com/api/registers/view";

import module namespace config="http://www.tei-c.org/tei-simple/config" at "config.xqm";
import module namespace pm-config="http://www.tei-c.org/tei-simple/pm-config" at "pm-config.xql";
import module namespace tpu="http://www.tei-c.org/tei-publisher/util" at "util.xql";
import module namespace vapi="http://teipublisher.com/api/view" at "lib/api/view.xql";
import module namespace page="http://teipublisher.com/ns/templates/page" at "templates/page.xqm";

declare namespace tei="http://www.tei-c.org/ns/1.0";

declare function rview:sort($people as array(*)*, $dir as xs:string) {
    let $sorted :=
        sort($people, "?lang=de-DE", function($entry) {
            $entry?1
        })
    return
        if ($dir = "asc") then
            $sorted
        else
            reverse($sorted)
};

declare function rview:people-all($request as map(*)) {
    let $people := collection($config:register-root)/id($config:register-map?person?id)//tei:person[ft:query(., '*', map {
        "leading-wildcard": "yes",
        "filter-rewrite": "yes"
    })]
    let $byKey := for-each($people, function($person as element()) {
        let $label := ft:field($person, "sort-name")
        return
            [lower-case($label), $person]
    })
    let $sorted := rview:sort($byKey, "asc")
    return array { 
        for $person in $sorted
        where $person?1
        return
            map {
                "id": $person?2/@xml:id/string(),
                "name": head(($person?2/tei:persName[@type="main"], $person?2/tei:persName[@type="canonical"], $person?2/tei:persName))/string(),
                "sort-name": $person?1
            }
     }
};

declare function rview:people-categories($request as map(*)){
    let $search := normalize-space($request?parameters?search)
    let $letterParam := $request?parameters?category
    let $sortDir := ($request?parameters?dir, 'asc')[1]
    let $limit := head(($request?parameters?limit, -1))
    let $show-notes := $request?parameters?description = 'on'
    let $odd := head(($request?parameters?odd, $config:default-odd))
    let $people :=
            if ($search and $search != '') then
                collection($config:register-root)/id($config:register-map?person?id)//tei:person[ft:query(., 'name:(' || $search || '*)')]
            else
                collection($config:register-root)/id($config:register-map?person?id)//tei:person[ft:query(., '*', map {
                        "leading-wildcard": "yes",
                        "filter-rewrite": "yes"
                    })]
    let $byKey := for-each($people, function($person as element()) {
        let $label := ft:field($person, "sort-name")
        return
            [lower-case($label), $label, $person]
    })
    let $sorted := rview:sort($byKey, $sortDir)
    let $letter := 
        if ($limit < 0 or count($people) < $limit) then 
            "all"
        else if ($letterParam = '') then
            substring($sorted[1]?1, 1, 1) => upper-case()
        else
            $letterParam
    let $byLetter :=
        if ($letter = 'all') then
            $sorted
        else
            filter($sorted, function($entry) {
                starts-with($entry?1, lower-case($letter))
            })
    return
        map {
            "items": rview:output-person-all($byLetter, $letter, $search, $odd, $show-notes),
            "categories":
                if (count($people) < $limit) then
                    []
                else array {
                    for $index in 1 to string-length('ABCDEFGHIJKLMNOPQRSTUVWXYZ')
                    let $alpha := substring('ABCDEFGHIJKLMNOPQRSTUVWXYZ', $index, 1)
                    let $hits := count(filter($sorted, function($entry) { starts-with($entry?1, lower-case($alpha))}))
                    where $hits > 0
                    return
                        map {
                            "category": $alpha,
                            "count": $hits
                        },
                    map {
                        "category": "all",
                        "count": count($sorted)
                    }
                }
        }
};

declare function rview:output-person-all($list as array(*)*, $letter as xs:string,  $search as xs:string?, $odd as xs:string, $show-notes as xs:boolean) {
    array {
        for $person in $list
        let $note := 
            $pm-config:web-transform($person?3, map { "mode": "register-overview", "show-notes": $show-notes }, $odd)
        return
            <div class="split-list-item">
            { $note }
            </div>
    }
};

declare function rview:detail-html($request as map(*)) {
    let $id := xmldb:decode-uri(xs:anyURI($request?parameters?id))
    let $entry := collection($config:data-root)/id($id) => head()
    let $config := tpu:parse-pi(root($entry), $request?parameters?view, $request?parameters?odd)
    let $mentions :=
        if ($entry instance of element(tei:person)) then
            collection($config:data-default)//tei:persName[@key = $id]/ancestor::tei:TEI
        else if ($entry instance of element(tei:bibl)) then
            collection($config:data-default)//tei:bibl[@key = $id]/ancestor::tei:TEI
        else if ($entry instance of element(tei:object)) then
            (: corpus documents carrying this authority id in msIdentifier :)
            collection($config:data-default)//tei:idno[@type = 'jinshi'][. = $id]/ancestor::tei:TEI
        else
            collection($config:data-default)//tei:placeName[@key = $id]/ancestor::tei:TEI
    let $extConfig := map {
        "entity-data": map {
            "id": $id,
            "root": $entry,
            "letters": $mentions,
            "transform": page:transform(?, ?, $config?odd),
            "transform-with": page:transform#3
        }
    }
    return
        vapi:html($request, $extConfig)
};

declare function rview:places($request as map(*)){
    let $search := normalize-space($request?parameters?search)
    let $letterParam := $request?parameters?category
    let $limit := $request?parameters?limit
    let $odd := head(($request?parameters?odd, $config:default-odd))
    let $show-notes := $request?parameters?description = 'on'
    let $places :=
        if ($search and $search != '') then 
            collection($config:places-root)//tei:place[ft:query(., 'name:(' || $search || '*)')]
        else
            collection($config:places-root)//tei:place
    let $sorted := sort($places, "?lang=de-DE", function($place) { lower-case(($place/tei:placeName)[1]) })
    let $letter := 
        if (count($places) < $limit) then 
            "all"
        else if ($letterParam = '') then
            substring($sorted[1], 1, 1) => upper-case()
        else
            $letterParam
    let $byLetter :=
        if ($letter = 'all') then
            $sorted
        else
            filter($sorted, function($entry) {
                starts-with(lower-case(($entry/tei:placeName)[1]), lower-case($letter))
            })
    return
        map {
            "items": rview:output-place($byLetter, $letter, $search, $odd, $show-notes),
            "categories":
                if (count($places) < $limit) then
                    []
                else array {
                    for $index in 1 to string-length('ABCDEFGHIJKLMNOPQRSTUVWXYZ')
                    let $alpha := substring('ABCDEFGHIJKLMNOPQRSTUVWXYZ', $index, 1)
                    let $hits := count(filter($sorted, function($entry) { starts-with(lower-case(($entry/tei:placeName)[1]), lower-case($alpha))}))
                    where $hits > 0
                    return
                        map {
                            "category": $alpha,
                            "count": $hits
                        },
                    map {
                        "category": "all",
                        "count": count($sorted)
                    }
                }
        }    
};

declare function rview:output-place($list, $category as xs:string, $search as xs:string?, $odd as xs:string, $show-notes as xs:boolean) {
    array {
        for $place in $list
       return
            <div class="place split-list-item">
            {$pm-config:web-transform(
                $place, 
                map { 
                "mode": "register-overview", 
                "show-notes": $show-notes }, 
                $odd)}
            </div>
    }
};

declare function rview:places-all($request as map(*)) {
    let $places := collection($config:places-root)//tei:place
    return 
        array { 
            for $place in $places[tei:location/tei:geo/text()]
                let $geo := $place/tei:location/tei:geo
                let $coords := tokenize($geo, ' ')
                return 
                    map {
                        "latitude":$coords[1],
                        "longitude":$coords[2],
                        "label":($place/tei:placeName)[1]/string(),
                        "id": $place/@xml:id/string()
                    }
            }        
};

declare function rview:geonames-link($id) {
    let $geo := substring-after($id, 'geo-')

    return
    if ($geo) then
            <a href="https://www.geonames.org/{$geo}" target="_blank">
                w geonames
                <iron-icon icon="maps:place"/> 
            </a>      
    else 
        ()
};

declare function rview:bibliography-all($request as map(*)) {
    (: all text content is used as label; scope to the bibliography register doc —
       an unscoped //tei:bibl would also return works, editions and attestations :)
    let $entries := collection($config:register-root)/id($config:register-map?bibliography?id)//tei:bibl
    let $byKey := for-each($entries, function($entry as element()) {
        let $label := normalize-space($entry)
        return
            [lower-case($label), $entry]
    })
    let $sorted := rview:sort($byKey, "asc")
    return array { 
        for $entry in $sorted
        where $entry?1
        return
            map {
                "id": $entry?2/@xml:id/string(),
                "name": normalize-space($entry?2)
            }
     }
};

declare function rview:bibliography-categories($request as map(*)){
    let $search := normalize-space($request?parameters?search)
    let $letterParam := $request?parameters?category
    let $sortDir := ($request?parameters?dir, 'asc')[1]
    let $limit := head(($request?parameters?limit, -1))
    let $odd := head(($request?parameters?odd, $config:default-odd))
    let $entries :=
            if ($search and $search != '') then
                collection($config:register-root)/id($config:register-map?bibliography?id)//tei:bibl[ft:query(., 'name:(' || $search || '*)')]
            else
                collection($config:register-root)/id($config:register-map?bibliography?id)//tei:bibl
    let $byKey := for-each($entries, function($entry as element()) {
        let $label := normalize-space($entry)
        return
            [lower-case($label), $label, $entry]
    })
    let $sorted := rview:sort($byKey, $sortDir)
    let $letter := 
        if ($limit < 0 or count($entries) < $limit) then 
            "all"
        else if ($letterParam = '') then
            substring($sorted[1]?1, 1, 1) => upper-case()
        else
            $letterParam
    let $byLetter :=
        if ($letter = 'all') then
            $sorted
        else
            filter($sorted, function($entry) {
                starts-with($entry?1, lower-case($letter))
            })
    return
        map {
            "items": rview:output-bibliography-all($byLetter, $letter, $search, $odd),
            "categories":
                if (count($entries) < $limit) then
                    []
                else array {
                    for $index in 1 to string-length('ABCDEFGHIJKLMNOPQRSTUVWXYZ')
                    let $alpha := substring('ABCDEFGHIJKLMNOPQRSTUVWXYZ', $index, 1)
                    let $hits := count(filter($sorted, function($entry) { starts-with($entry?1, lower-case($alpha))}))
                    where $hits > 0
                    return
                        map {
                            "category": $alpha,
                            "count": $hits
                        },
                    map {
                        "category": "all",
                        "count": count($sorted)
                    }
                }
        }
};

declare function rview:output-bibliography-all($list as array(*)*, $letter as xs:string,  $search as xs:string?, $odd as xs:string) {
    array {
        for $entry in $list
        let $letterParam := if ($letter = "all") then substring($entry?3/@n, 1, 1) else $letter
        let $note :=
            $pm-config:web-transform($entry?3, map { "mode": "register-overview" }, $odd)
        return
            <div class="split-list-item">
            { $note }
            </div>
    }
};

(: ===================================================================
 : Jinshi history layer (doc/sino-model.md par.10): the works register
 : 金石著作 (pb-works, bibl type="work") and the inscription authority
 : register 石刻總目 (pb-jinshi, listObject/object). Lists sort and
 : categorise by the romanised sort title so the pb-split-list A–Z
 : navigation works for Chinese-titled material.
 : =================================================================== :)

declare %private function rview:work-sort-label($bibl as element()) as xs:string {
    normalize-space(head(($bibl/tei:title[@xml:lang = 'zh-Latn-x-pinyin'],
        $bibl/tei:title[@type = 'sort'], $bibl/tei:title)))
};

declare %private function rview:object-sort-label($object as element()) as xs:string {
    normalize-space(head(($object//tei:objectName[@type = 'sort'],
        $object//tei:objectName)))
};

declare %private function rview:works($search as xs:string?) {
    let $root := collection($config:register-root)/id($config:register-map?work?id)
    return
        if ($search and $search != '') then
            $root//tei:bibl[@type = 'work'][ft:query(., 'name:(' || $search || '*)')]
        else
            $root//tei:bibl[@type = 'work']
};

declare %private function rview:jinshi-objects($search as xs:string?) {
    let $root := collection($config:register-root)/id($config:register-map?inscription?id)
    return
        if ($search and $search != '') then
            $root//tei:object[ft:query(., 'name:(' || $search || '*)')]
        else
            $root//tei:object
};

declare function rview:works-all($request as map(*)) {
    array {
        for $bibl in rview:works(())
        let $label := rview:work-sort-label($bibl)
        order by lower-case($label) collation "?lang=de-DE"
        return
            map {
                "id": $bibl/@xml:id/string(),
                "name": head(($bibl/tei:title[@xml:lang = 'zh'], $bibl/tei:title))/string(),
                "sort-name": $label
            }
    }
};

declare function rview:jinshi-all($request as map(*)) {
    array {
        for $object in rview:jinshi-objects(())
        let $label := rview:object-sort-label($object)
        order by lower-case($label) collation "?lang=de-DE"
        return
            map {
                "id": $object/@xml:id/string(),
                "name": head(($object//tei:objectName[@type = 'main'], $object//tei:objectName))/string(),
                "sort-name": $label,
                "date": $object//tei:origin/tei:origDate/@when/string()
            }
    }
};

(:~ Shared A–Z categories listing for register entries keyed by a sort label. :)
declare %private function rview:register-categories($entries as element()*, $request as map(*),
        $label-fn as function(*), $output-fn as function(*)) {
    let $letterParam := $request?parameters?category
    let $sortDir := ($request?parameters?dir, 'asc')[1]
    let $limit := head(($request?parameters?limit, -1))
    let $odd := head(($request?parameters?odd, $config:default-odd))
    let $byKey := for-each($entries, function($entry as element()) {
        let $label := $label-fn($entry)
        return
            [lower-case($label), $label, $entry]
    })
    let $sorted := rview:sort($byKey, $sortDir)
    let $letter :=
        if ($limit < 0 or count($entries) < $limit) then
            "all"
        else if ($letterParam = '') then
            substring($sorted[1]?1, 1, 1) => upper-case()
        else
            $letterParam
    let $byLetter :=
        if ($letter = 'all') then
            $sorted
        else
            filter($sorted, function($entry) {
                starts-with($entry?1, lower-case($letter))
            })
    return
        map {
            "items": $output-fn($byLetter, $odd),
            "categories":
                if (count($entries) < $limit) then
                    []
                else array {
                    for $index in 1 to string-length('ABCDEFGHIJKLMNOPQRSTUVWXYZ')
                    let $alpha := substring('ABCDEFGHIJKLMNOPQRSTUVWXYZ', $index, 1)
                    let $hits := count(filter($sorted, function($entry) { starts-with($entry?1, lower-case($alpha))}))
                    where $hits > 0
                    return
                        map {
                            "category": $alpha,
                            "count": $hits
                        },
                    map {
                        "category": "all",
                        "count": count($sorted)
                    }
                }
        }
};

declare %private function rview:output-register-entries($list as array(*)*, $odd as xs:string) {
    array {
        for $entry in $list
        return
            <div class="split-list-item">
            { $pm-config:web-transform($entry?3, map { "mode": "register-overview" }, $odd) }
            </div>
    }
};

declare function rview:works-categories($request as map(*)) {
    let $search := normalize-space($request?parameters?search)
    return
        rview:register-categories(rview:works($search), $request,
            rview:work-sort-label#1, rview:output-register-entries#2)
};

declare function rview:jinshi-categories($request as map(*)) {
    let $search := normalize-space($request?parameters?search)
    return
        rview:register-categories(rview:jinshi-objects($search), $request,
            rview:object-sort-label#1, rview:output-register-entries#2)
};

(: ─── Rubbing Collections ──────────────────────────────────────────────── :)

declare %private function rview:collection-sort-label($org as element()) as xs:string {
    normalize-space(head(($org/tei:orgName[@type='sort'],
        $org/tei:orgName[@type='main'], $org/tei:orgName)))
};

declare %private function rview:collections($search as xs:string?) {
    let $root := collection($config:register-root)/id($config:register-map?collection?id)
    return
        if ($search and $search != '') then
            $root//tei:org[ft:query(., 'name:(' || $search || '*)')]
        else
            $root//tei:org
};

declare function rview:collections-all($request as map(*)) {
    array {
        for $org in rview:collections(())
        let $label := rview:collection-sort-label($org)
        order by lower-case($label) collation "?lang=de-DE"
        return
            map {
                "id": $org/@xml:id/string(),
                "name": head(($org/tei:orgName[@type='main'], $org/tei:orgName))/string(),
                "sort-name": $label,
                "country": $org/tei:country/@key/string()
            }
    }
};

declare function rview:collections-categories($request as map(*)) {
    let $search := normalize-space($request?parameters?search)
    return
        rview:register-categories(rview:collections($search), $request,
            rview:collection-sort-label#1, rview:output-register-entries#2)
};

(: ─── Rubbings (拓片) ───────────────────────────────────────────────────── :)

declare %private function rview:rubbing-sort-label($obj as element()) as xs:string {
    normalize-space(head(($obj//tei:objectName[@type='sort'],
        $obj//tei:objectName[@type='main'], $obj//tei:objectName)))
};

declare %private function rview:rubbings($search as xs:string?) {
    let $root := collection($config:register-root)/id($config:register-map?rubbing?id)
    return
        if ($search and $search != '') then
            $root//tei:object[@type='rubbing'][ft:query(., 'name:(' || $search || '*)')]
        else
            $root//tei:object[@type='rubbing']
};

declare function rview:rubbings-all($request as map(*)) {
    array {
        for $obj in rview:rubbings(())
        let $label := rview:rubbing-sort-label($obj)
        order by lower-case($label) collation "?lang=de-DE"
        return
            map {
                "id": $obj/@xml:id/string(),
                "name": head(($obj//tei:objectName[@type='main'], $obj//tei:objectName))/string(),
                "sort-name": $label,
                "collection": ($obj//tei:objectIdentifier/tei:repository/@corresp)[1]/string(),
                "inscription": $obj/@corresp/string()
            }
    }
};

declare function rview:rubbings-categories($request as map(*)) {
    let $search := normalize-space($request?parameters?search)
    return
        rview:register-categories(rview:rubbings($search), $request,
            rview:rubbing-sort-label#1, rview:output-register-entries#2)
};