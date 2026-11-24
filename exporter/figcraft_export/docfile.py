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


def extras(saveas_reply):
    """{layer id (str): {"overflow", "position", "varModes"}} for layers that set any of them."""
    try:
        doc = json.loads(document_bytes(saveas_reply).decode("utf-8"))
        nodes = doc.get("nodes") or {}
    except (ValueError, UnicodeDecodeError, AttributeError):
        raise DocFileError("Impossible de lire le document FigCraft (document.json illisible).")
    out = {}
    for key, n in nodes.items():
        if not isinstance(n, dict):
            continue
        overflow = n.get("overflow")
        position = n.get("scroll_position")
        modes = n.get("var_modes")
        if overflow is None and position is None and not modes:
            continue
        out[str(key)] = {
            "overflow": overflow or "none",
            "position": _POSITIONS.get(position, "scroll"),
            "varModes": {str(k): v for k, v in (modes or {}).items() if v is not None},
        }
    return out
