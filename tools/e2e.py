#!/usr/bin/env python3
"""Bout en bout : ouvre une copie d'un exemple .figcraft dans son propre FigCraft, sélectionne
des frames, lance l'export, rend des PNG de référence, vérifie, puis quitte FigCraft sans
rien enregistrer. Python 3.8+, bibliothèque standard seulement.

    python3 tools/e2e.py examples/ridgeline-onboarding.figcraft [--frames "A,B"] [--out dossier]
                         [--use-dist] [--keep-open]

Sans --frames : toutes les frames de premier niveau de la page courante.
Sans --out : un dossier temporaire (affiché à la fin).
Les PNG de référence vont dans <out>/_reference/, à côté de l'export (jamais dedans).
--use-dist : lance l'export depuis dist/FigCraft Export HTML/ (lancez make_dist.py avant).
"""
import argparse
import base64
import os
import shutil
import socket
import subprocess
import sys
import tempfile
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
EXPORTER = ROOT / "exporter"
DIST = ROOT / "dist" / "FigCraft Export HTML"
sys.path.insert(0, str(EXPORTER))

from figcraft_export import launcher, summary, writer  # noqa: E402
from figcraft_export.control import Control, ControlError  # noqa: E402


class E2EError(Exception):
    pass


def free_port():
    s = socket.socket()
    s.bind(("127.0.0.1", 0))
    port = s.getsockname()[1]
    s.close()
    return port


def same_path(a, b):
    try:
        return os.path.realpath(a) == os.path.realpath(b)
    except (OSError, TypeError):
        return False


def open_copy(ctl, copy):
    """Switch to the tab holding our copy (FigCraft may also reopen old unsaved tabs)."""
    docs = ctl.execute("doc.list", {})
    mine = [d for d in docs if d.get("path") and same_path(d["path"], copy)]
    if not mine:
        raise E2EError("FigCraft n'a pas ouvert la copie de l'exemple.")
    if not mine[0].get("active"):
        ctl.execute("doc.switch", {"index": mine[0]["index"]})
    info = ctl.request("document.inspect", {"depth": 1})
    if not info.get("path") or not same_path(info["path"], copy):
        raise E2EError("Le document actif n'est pas la copie de l'exemple.")
    return info


def top_frames(info):
    page = next((p for p in info["pages"] if p["id"] == info["currentPage"]), None)
    if page is None:
        raise E2EError("Page courante introuvable.")
    out = []
    for n in page.get("children", []):
        if n.get("type") == "FRAME":
            out.append(n)
        elif n.get("type") == "SECTION":
            out += [c for c in n.get("children", []) if c.get("type") == "FRAME"]
    return out


def check_redo(ctl):
    """After an export, the redo stack may hold only our final no-op ("Export HTML (fin) ...")."""
    from figcraft_export import docfile
    from figcraft_export.edits import BATCH_LABEL, FINAL_LABEL
    hist = ctl.request("document.inspect", {"depth": 0}).get("history") or {}
    redo = hist.get("redo") or 0
    redo = len(redo) if isinstance(redo, list) else int(redo)
    print("Historique après l'export : %d étape(s) à annuler, %d à rétablir." % (len(hist.get("undo") or []), redo))
    if redo == 0:
        return
    if redo != 1:
        raise E2EError("La pile Rétablir contient %d étapes (au plus 1 attendue)." % redo)
    d0 = docfile.digest(ctl.execute("file.saveAs", {"data": True}))
    ctl.execute("edit.redo", {})
    top = (ctl.request("document.inspect", {"depth": 0}).get("history") or {}).get("undo") or [None]
    same = docfile.digest(ctl.execute("file.saveAs", {"data": True})) == d0
    ctl.execute("edit.undo", {})
    print("Rétablir referait : %s (document inchangé : %s)." % (top[0], "oui" if same else "non"))
    if not str(top[0]).startswith(FINAL_LABEL) or str(top[0]).startswith(BATCH_LABEL) or not same:
        raise E2EError("Rétablir juste après l'export referait une modification : %s." % top[0])


def close_mine(ctl, copy):
    try:
        for d in ctl.execute("doc.list", {}):
            if d.get("path") and same_path(d["path"], copy):
                ctl.execute("file.close", {"index": d["index"], "force": True})
    except Exception:
        pass


def run(args):
    example = Path(args.example).resolve()
    if not example.is_file():
        raise E2EError("Exemple introuvable : %s" % example)
    work = Path(tempfile.mkdtemp(prefix="figcraft-e2e-"))
    copy = work / example.name
    shutil.copyfile(str(example), str(copy))
    out = Path(args.out) if args.out else work / "export"
    figcraft = launcher.find_figcraft(launcher.load_config())
    if figcraft is None:
        raise E2EError("FigCraft est introuvable.")
    cwd = DIST if args.use_dist else EXPORTER
    if args.use_dist and not (DIST / "figcraft_export").is_dir():
        raise E2EError("dist/FigCraft Export HTML est absent : lancez tools/make_dist.py.")
    port = free_port()
    print("Lancement de FigCraft (port %d), copie : %s" % (port, copy))
    proc = launcher.launch(figcraft, port, copy)
    ctl = Control(port)
    try:
        if not launcher.wait_ready(port, 40):
            raise E2EError("FigCraft ne répond pas sur le port %d." % port)
        time.sleep(1.5)
        info = open_copy(ctl, copy)
        frames = top_frames(info)
        if args.frames:
            wanted = [w.strip() for w in args.frames.split(",") if w.strip()]
            chosen = []
            for w in wanted:
                hit = [f for f in frames if f["name"] == w]
                if not hit:
                    raise E2EError("Frame introuvable sur la page courante : « %s » (frames : %s)."
                                   % (w, ", ".join(f["name"] for f in frames)))
                chosen.append(hit[0])
        else:
            chosen = frames
        if not chosen:
            raise E2EError("Aucune frame de premier niveau à exporter.")
        ids = [f["id"] for f in chosen]
        ctl.execute("select.set", {"ids": ids})
        sel = ctl.request("document.inspect", {"depth": 0}).get("selection")
        if sorted(sel or []) != sorted(ids):
            raise E2EError("La sélection n'a pas pris : %s au lieu de %s." % (sel, ids))
        print("Sélection : %s" % ", ".join("%s (%s)" % (f["name"], f["id"]) for f in chosen))

        cmd = [sys.executable, "-m", "figcraft_export", "export", "--port", str(port),
               "--out", str(out), "--no-open"]
        env = dict(os.environ, PYTHONIOENCODING="utf-8")
        r = subprocess.run(cmd, cwd=str(cwd), env=env, stdin=subprocess.DEVNULL,
                           stdout=subprocess.PIPE, stderr=subprocess.STDOUT, timeout=600)
        text = r.stdout.decode("utf-8", "replace")
        print(text.rstrip())
        if r.returncode != 0:
            raise E2EError("L'export a échoué (code %d)." % r.returncode)
        if summary.DIGEST_OK not in text:
            raise E2EError("Le résumé ne confirme pas que le document est inchangé.")
        folders = [p for p in out.iterdir() if (p / "index.html").is_file()] if out.is_dir() else []
        if not folders:
            raise E2EError("Aucun index.html dans %s." % out)
        target = folders[0]
        check_redo(ctl)

        ref = out / "_reference"
        ref.mkdir(exist_ok=True)
        used = set()
        for f in chosen:
            reply = ctl.execute("file.export", {"ids": [f["id"]], "format": "png", "scale": 1},
                                timeout_ms=120000)
            name = writer.slug(f["name"])
            while name in used:
                name += "-%s" % f["id"]
            used.add(name)
            (ref / ("%s.png" % name)).write_bytes(base64.b64decode(reply["data"]))
        print("Références PNG : %d dans %s" % (len(chosen), ref))
        return target
    finally:
        ctl.close()
        if not args.keep_open:
            c2 = Control(port)
            try:
                close_mine(c2, copy)
                try:
                    c2.request("app.quit", {}, timeout_ms=5000)
                except Exception:
                    pass
            finally:
                c2.close()
            try:
                proc.wait(timeout=8)
            except subprocess.TimeoutExpired:
                proc.kill()
        if args.out:
            shutil.rmtree(str(copy.parent), ignore_errors=True)


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("example")
    p.add_argument("--frames")
    p.add_argument("--out")
    p.add_argument("--use-dist", action="store_true")
    p.add_argument("--keep-open", action="store_true")
    args = p.parse_args(argv)
    try:
        target = run(args)
    except E2EError as e:
        print("ÉCHEC : %s" % e, file=sys.stderr)
        return 1
    except (ControlError, OSError, subprocess.SubprocessError) as e:
        print("ÉCHEC : %s" % e, file=sys.stderr)
        return 1
    print("OK. Dossier exporté : %s" % target)
    return 0


if __name__ == "__main__":
    sys.exit(main())
