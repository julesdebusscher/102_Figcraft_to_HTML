#!/bin/bash
# Runs every player/test/*.test.js under JavaScriptCore. Works from any cwd.
set -u
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SRC="$HERE/../src"
JSC="${JSC:-/System/Library/Frameworks/JavaScriptCore.framework/Versions/Current/Helpers/jsc}"
TMP="$(mktemp)"
trap 'rm -f "$TMP"' EXIT
{
  echo "load(\"$HERE/harness.js\");"
  while IFS= read -r f || [ -n "$f" ]; do
    [ -z "$f" ] && continue
    echo "load(\"$SRC/$f\");"
  done < "$SRC/ORDER"
  for t in "$HERE"/*.test.js; do echo "load(\"$t\");"; done
  echo "if (!__report()) throw new Error('tests failed');"
} > "$TMP"
"$JSC" "$TMP"
