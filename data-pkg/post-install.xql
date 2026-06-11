xquery version "3.1";

import module namespace xdb="http://exist-db.org/xquery/xmldb";

(: The following external variables are set by the repo:deploy function :)

(: file path pointing to the exist installation directory :)
declare variable $home external;
(: path to the directory containing the unpacked .xar package :)
declare variable $dir external;
(: the target collection into which the app is deployed :)
declare variable $target external;

declare function local:mkcol($collection, $path) {
    for $component at $i in tokenize($path, "/")
    let $parent := string-join(($collection, subsequence(tokenize($path, "/"), 1, $i - 1)), "/")
    return
        if (xmldb:collection-available($parent || "/" || $component)) then
            ()
        else
            xdb:create-collection($parent, $component)
};

declare function local:own($path as xs:string) {
    sm:chown(xs:anyURI($path), "tei"),
    sm:chgrp(xs:anyURI($path), "tei"),
    sm:chmod(xs:anyURI($path), "rwxrwxr-x")
};

(: collections the application expects below data/ — empty ones are not preserved by the xar :)
for $col in ("workspace", "places", "people", "registers", "registers/templates", "taxonomy", "zotero", "zotero/groups")
return (
    local:mkcol($target || "/data", $col),
    local:own($target || "/data/" || $col)
),

(: inscriptions must be group-writable for editors :)
for $resource in xmldb:get-child-resources($target || "/data/workspace")
return
    sm:chmod(xs:anyURI($target || "/data/workspace/" || $resource), "rw-rw-r--"),

(: apply the index configuration stored by pre-install :)
xdb:reindex($target || "/data")
