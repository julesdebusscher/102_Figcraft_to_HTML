"""Output folder: index.html, player.js, player.css, data.js, assets/ (opens from file://)."""
import html
import json
import os
import re
import shutil
import unicodedata
from pathlib import Path, PurePosixPath

DATA_PREFIX = "window.FIGCRAFT_PROTOTYPE = "
_RESERVED = {"con", "prn", "aux", "nul"} | {"com%d" % i for i in range(1, 10)} | {"lpt%d" % i for i in range(1, 10)}
_TITLE = re.compile(r"<title>.*?</title>", re.S)


class WriteError(Exception):
    """The folder cannot be written (message in French, shown as is)."""


def slug(title):
    """'Mon proto / v2' -> 'mon-proto-v2'; ASCII letters, digits and '-' only; 'prototype' if empty."""
    text = unicodedata.normalize("NFKD", str(title or ""))
    text = "".join(c for c in text if not unicodedata.combining(c)).lower()
    text = re.sub(r"[^a-z0-9]+", "-", text).strip("-")[:60].strip("-")
    if not text:
        return "prototype"
    if text in _RESERVED:
        return text + "-prototype"
    return text


def to_data_js(proto):
    """`window.FIGCRAFT_PROTOTYPE = <json>;` safe inside a classic <script> (no '</')."""
    body = json.dumps(proto, ensure_ascii=False, separators=(",", ":"))
    body = body.replace("</", "<\\/").replace("\u2028", "\\u2028").replace("\u2029", "\\u2029")
    return DATA_PREFIX + body + ";\n"


def _read(path):
    with open(str(path), "r", encoding="utf-8") as f:
        return f.read()


def player_js(player_root):
    """The prebuilt player.js if present, else src/*.js concatenated in src/ORDER's order."""
    root = Path(player_root)
    if (root / "player.js").is_file():
        return _read(root / "player.js")
    order = [l.strip() for l in _read(root / "src" / "ORDER").splitlines()]
    parts = [_read(root / "src" / name) for name in order if name and not name.startswith("#")]
    return "\n".join(p if p.endswith("\n") else p + "\n" for p in parts)


def index_html(player_root, title):
    page = _read(Path(player_root) / "index.html")
    return _TITLE.sub(lambda m: "<title>%s</title>" % html.escape(title or "Prototype"), page, count=1)


def _write_bytes(path, data):
    with open(str(path), "wb") as f:
        f.write(data)


def _write_text(path, text):
    _write_bytes(path, text.encode("utf-8"))


def _asset_target(folder, rel):
    parts = PurePosixPath(str(rel)).parts
    if not parts or parts[0] != "assets" or any(p in ("", ".", "..") or "\\" in p or ":" in p for p in parts):
        raise WriteError("Nom de fichier inattendu : %s" % rel)
    return folder.joinpath(*parts)


def _remove(path):
    if path.is_dir():
        shutil.rmtree(str(path), ignore_errors=True)


def _rename(src, dst):
    Path(src).rename(dst)


def _is_export(folder):
    """True when folder/data.js is one of ours (starts with DATA_PREFIX)."""
    try:
        with open(str(folder / "data.js"), "rb") as f:
            return f.read(len(DATA_PREFIX)) == DATA_PREFIX.encode("ascii")
    except OSError:
        return False


def write(out_dir, proto, assets, player_root):
    """Write the export into out_dir/<slug(title)>/ and return that folder.

    Everything is written into a hidden sibling folder `.<slug>.export-<pid>` first, then
    swapped in: an earlier export is renamed `.<slug>.old-<pid>`, the new one renamed to
    <slug>, then the old one deleted (renamed back if the swap fails). An error leaves no
    partial folder and the earlier export in place. Leftover `.<slug>.export-*`/`.old-*`
    folders of an interrupted run are removed. An existing target is replaced only when it is
    empty or holds an earlier export (data.js starting with DATA_PREFIX); otherwise WriteError."""
    out_dir = Path(out_dir)
    name = slug(proto.get("title"))
    target = out_dir / name
    if target.exists():
        if not target.is_dir():
            raise WriteError("« %s » existe déjà et n'est pas un dossier." % target)
        if any(target.iterdir()) and not _is_export(target):
            raise WriteError("Le dossier « %s » existe déjà et ne contient pas un export : "
                             "choisissez un autre dossier ou videz-le." % target)
    for pattern in (".%s.export-*" % name, ".%s.old-*" % name):
        for left in out_dir.glob(pattern):
            _remove(left)
    tmp = out_dir / (".%s.export-%d" % (name, os.getpid()))
    old = out_dir / (".%s.old-%d" % (name, os.getpid()))
    try:
        tmp.mkdir()
        (tmp / "assets").mkdir()
        for a in assets:
            dest = _asset_target(tmp, a["path"])
            dest.parent.mkdir(parents=True, exist_ok=True)
            _write_bytes(dest, a["data"])
        _write_text(tmp / "data.js", to_data_js(proto))
        _write_text(tmp / "player.js", player_js(player_root))
        _write_bytes(tmp / "player.css", (Path(player_root) / "player.css").read_bytes())
        _write_text(tmp / "index.html", index_html(player_root, proto.get("title")))
        moved = False
        if target.exists():
            _rename(target, old)
            moved = True
        try:
            _rename(tmp, target)
        except BaseException as e:
            if moved:
                try:
                    _rename(old, target)
                except OSError:
                    raise WriteError(
                        "Impossible d'écrire l'export (%s). L'export précédent se trouve maintenant dans "
                        "« %s » ; le prochain export dans ce dossier le supprimera : copiez-le ailleurs "
                        "pour le garder." % (e, old))
            raise
    except BaseException:
        _remove(tmp)
        raise
    _remove(old)
    return target
