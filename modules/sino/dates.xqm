xquery version "3.1";

(:~
 : EDEp Sino — Chinese era-date conversion service (doc/sino-model.md par.1).
 :
 : Backed by data/taxonomy/nianhao.xml, derived from the DDBC Time Authority
 : (CC BY-SA 3.0). Reign-year ranges are exact lunisolar spans converted to
 : proleptic-Gregorian ISO dates, so @notBefore/@notAfter carry the true
 : straddle of a Chinese year over two western years; @when is the western
 : year in which the reign year begins (conventional equivalence).
 :
 : Returns XML (not JSON) so the editor can bind the result as a Fore
 : instance directly.
 :)
module namespace sino-dates="http://edep-sino.org/api/sino/dates";

import module namespace config="http://www.tei-c.org/tei-simple/config" at "../config.xqm";

declare namespace tei="http://www.tei-c.org/ns/1.0";

declare variable $sino-dates:GAN := "甲乙丙丁戊己庚辛壬癸";
declare variable $sino-dates:ZHI := "子丑寅卯辰巳午未申酉戌亥";
declare variable $sino-dates:DIGITS := "一二三四五六七八九";

declare variable $sino-dates:table := doc($config:data-root || "/taxonomy/nianhao.xml")/nianhao;
declare variable $sino-dates:dynasties := doc($config:data-root || "/taxonomy/dynasty.xml")/tei:taxonomy;

(:~ Cyclical year of a (proleptic Gregorian) western year :)
declare function sino-dates:ganzhi($year as xs:integer) as xs:string {
    let $i := ($year - 4) mod 60
    let $i := if ($i < 0) then $i + 60 else $i
    return
        substring($sino-dates:GAN, $i mod 10 + 1, 1) || substring($sino-dates:ZHI, $i mod 12 + 1, 1)
};

(:~ Chinese numeral for a reign year (1 -> 元, 14 -> 十四, 31 -> 三十一) :)
declare function sino-dates:year-numeral($n as xs:integer) as xs:string {
    if ($n = 1) then "元"
    else if ($n < 10) then substring($sino-dates:DIGITS, $n, 1)
    else if ($n = 10) then "十"
    else if ($n < 20) then "十" || substring($sino-dates:DIGITS, $n mod 10, 1)
    else
        substring($sino-dates:DIGITS, $n idiv 10, 1) || "十" ||
        (if ($n mod 10 = 0) then "" else substring($sino-dates:DIGITS, $n mod 10, 1))
};

(:~ Map a DDBC dynasty name to the sino dynasty taxonomy CURIE, if known :)
declare %private function sino-dates:period($dynasty as xs:string) as xs:string? {
    $sino-dates:dynasties/tei:category[tei:catDesc[@xml:lang = 'zh'] = $dynasty]/@corresp/string()
};

declare %private function sino-dates:era-output($era as element(era), $year as xs:integer?, $ganzhi as xs:string?) as element(era) {
    let $y := if (exists($year)) then $era/y[@n = string($year)] else ()
    return
        <era id="{$era/@xml:id}" name="{$era/@name}" dynasty="{$era/@dynasty}"
             emperor="{$era/@emperor}" eraFrom="{$era/@from}" eraTo="{$era/@to}">
        {
            attribute period { (sino-dates:period($era/@dynasty), '')[1] },
            if ($y) then (
                attribute year { $year },
                attribute nToken { $era/@name || sino-dates:year-numeral($year) || "年" },
                attribute when { substring($y/@from, 1, 4) },
                attribute notBefore { $y/@from/string() },
                attribute notAfter { $y/@to/string() },
                attribute gz { $y/@gz/string() },
                if (exists($ganzhi) and $ganzhi != '') then
                    attribute gzMatch { if ($y/@gz = $ganzhi) then 'true' else 'false' }
                else ()
            ) else if (exists($year)) then
                attribute yearOutOfRange { 'true' }
            else (
                attribute notBefore { $era/@from/string() },
                attribute notAfter { $era/@to/string() }
            )
        }
        </era>
};

(:~
 : GET /api/sino/era?name=永和&year=9&ganzhi=癸丑&dynasty=東晉
 : Era name may match the primary name or an attested variant (@alt).
 : Returns all candidate eras (era names repeat across dynasties).
 :)
declare function sino-dates:era($request as map(*)) {
    let $name := normalize-space($request?parameters?name)
    let $year := $request?parameters?year
    let $ganzhi := normalize-space($request?parameters?ganzhi)
    let $dynasty := normalize-space($request?parameters?dynasty)
    let $candidates :=
        $sino-dates:table/era[@name = $name or tokenize(@alt, '\s+') = $name]
            [if ($dynasty != '') then @dynasty = $dynasty else true()]
    return
        <result name="{$name}" count="{count($candidates)}">
        {
            if (exists($year)) then attribute year { $year } else (),
            if ($ganzhi != '') then attribute ganzhi { $ganzhi } else (),
            for $era in $candidates
            order by xs:integer($era/@from)
            return
                sino-dates:era-output($era, if ($year castable as xs:integer) then xs:integer($year) else (), $ganzhi)
        }
        </result>
};

(:~
 : GET /api/sino/eras — the full era list, for the form's autocomplete.
 :)
declare function sino-dates:eras($request as map(*)) {
    <eras>
    {
        for $era in $sino-dates:table/era
        order by xs:integer($era/@from)
        return
            <e n="{$era/@name}" d="{$era/@dynasty}" f="{$era/@from}" t="{$era/@to}"/>
    }
    </eras>
};
