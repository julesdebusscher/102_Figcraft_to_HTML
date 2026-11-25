"""document.json from a `file.saveAs {data:true}` reply: per-layer extras and digest.

The reply is {bytes, data, name}; `data` is the base64 .figcraft file, a zip holding
`document.json` (and `thumbnail.png`). node.get cannot read `overflow`, `scroll_position`
and `var_modes`; the file can (see docs/figcraft-api-notes.md, "document.json").
"""
import base64
import binascii
import hashlib
import io
import json
import zipfile

_POSITIONS = {"scrolls": "scroll", "fixed": "fixed", "sticky": "sticky"}


class DocFileError(Exception):
    """The saved file could not be read (message in French)."""


def document_bytes(saveas_reply):
    """Raw bytes of document.json inside the saved file."""
    try:
        raw = base64.b64decode((saveas_reply or {}).get("data") or "", validate=False)
        with zipfile.ZipFile(io.BytesIO(raw)) as z:
            return z.read("document.json")
    except (binascii.Error, zipfile.BadZipFile, KeyError, ValueError, TypeError, AttributeError):
        raise DocFileError("Impossible de lire le document FigCraft (copie enregistrée illisible).")


def digest(saveas_reply):
    """sha256 (hex) of document.json: equal before/after the export = document untouched."""
    return hashlib.sha256(document_bytes(saveas_reply)).hexdigest()


def _page_of(nodes, n):
    """Id (str) of the page a top-level layer sits on (through sections), else None."""
    cur, guard = nodes.get(str(n.get("parent"))), 0
    while isinstance(cur, dict) and guard < 1000:
        guard += 1
        if cur.get("type") == "page":
            return str(cur.get("id"))
        if cur.get("type") != "section":
            return None
        cur = nodes.get(str(cur.get("parent")))
    return None


def extras(saveas_reply):
    """{layer id (str): {"overflow", "position", "varModes", "page"?}} for layers that set any of
    them; "page" (the page id) for the top-level layers of a page that sets modes itself
    (`var_modes` on the page, as `variable.setMode {ids:[page]}` writes)."""
    try:
        doc = json.loads(document_bytes(saveas_reply).decode("utf-8"))
        nodes = doc.get("nodes") or {}
    except (ValueError, UnicodeDecodeError, AttributeError):
        raise DocFileError("Impossible de lire le document FigCraft (document.json illisible).")
    moded = set(str(k) for k, n in nodes.items()
                if isinstance(n, dict) and n.get("type") == "page" and n.get("var_modes"))
    out = {}
    for key, n in nodes.items():
        if not isinstance(n, dict):
            continue
        overflow = n.get("overflow")
        position = n.get("scroll_position")
        modes = n.get("var_modes")
        page = _page_of(nodes, n) if moded and n.get("type") not in ("page", "section") else None
        if page not in moded:
            page = None
        if overflow is None and position is None and not modes and page is None:
            continue
        out[str(key)] = {
            "overflow": overflow or "none",
            "position": _POSITIONS.get(position, "scroll"),
            "varModes": {str(k): v for k, v in (modes or {}).items() if v is not None},
        }
        if page is not None:
            out[str(key)]["page"] = page
    return out
