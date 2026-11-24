"""Command line: python -m figcraft_export launch|export."""
import argparse
import sys
import webbrowser
from pathlib import Path

from . import MIN_VERSION, version_ok
from .control import DEFAULT_PORT, Control, ControlError, Unreachable
from . import docfile, launcher, render, summary, variables, walk, writer

NO_TOUCH = "Ne modifiez pas le document dans FigCraft pendant l'export."
NOTHING_WRITTEN = "Aucun fichier n'a été écrit."


def _setup_console():
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8", errors="replace")
        except Exception:
            pass


def _say(text):
    print(text)


def _fail(text):
    print(text, file=sys.stderr)
    return 1


def _resolve_figcraft(cfg, ask=True):
    path = launcher.find_figcraft(cfg)
    if path is None and ask and sys.stdin is not None and sys.stdin.isatty():
        raw = input("FigCraft est introuvable. Chemin de FigCraft.exe : ").strip().strip('"')
        if raw and Path(raw).is_file():
            path = Path(raw)
            cfg["figcraft_path"] = str(path)
            try:
                launcher.save_config(launcher.package_dir(), cfg)
            except OSError as e:
                _say("Avertissement : impossible d'enregistrer le chemin (%s)." % e)
        elif raw:
            _say("Fichier introuvable : %s" % raw)
    return path


def cmd_launch(args):
    cfg = launcher.load_config()
    path = _resolve_figcraft(cfg)
    if path is None:
        return _fail("FigCraft est introuvable. Installez-le ou indiquez son chemin.")
    version = launcher.app_version(path)
    if version is not None and not version_ok(version):
        return _fail(_too_old(version))
    launcher.launch(path, args.port, args.file)
    _say("FigCraft démarre (port %d)..." % args.port)
    if launcher.wait_ready(args.port):
        _say("FigCraft est prêt.")
        return 0
    return _fail("FigCraft ne répond pas après 20 secondes (port %d)." % args.port)


def _too_old(found):
    return "FigCraft %s ou plus récent est nécessaire (trouvé : %s)." % (
        ".".join(str(n) for n in MIN_VERSION),
        found,
    )


def cmd_export(args):
    control = Control(args.port)
    try:
        control.request("document.inspect", {"depth": 0}, timeout_ms=10000)
    except Unreachable:
        return _fail(
            "Impossible de joindre FigCraft. Ouvrez-le avec « Ouvrir FigCraft »."
        )
    except BaseException:
        control.close()
        raise
    try:
        path = launcher.find_figcraft(launcher.load_config())
        version = launcher.app_version(path) if path else None
        if version is not None and not version_ok(version):
            return _fail(_too_old(version))
        return _export(control, args)
    finally:
        control.close()


def player_root(pkg=None):
    """figcraft_export/player (distribution) if present, else the repository's player/."""
    pkg = Path(pkg) if pkg else Path(__file__).resolve().parent
    if (pkg / "player" / "index.html").is_file():
        return pkg / "player"
    return pkg.parent.parent / "player"


def _ask_folder():
    """A folder picker (tkinter), else a typed path; None when cancelled."""
    try:
        import tkinter
        from tkinter import filedialog

        root = tkinter.Tk()
        root.withdraw()
        try:
            root.attributes("-topmost", True)
        except Exception:
            pass
        try:
            chosen = filedialog.askdirectory(parent=root, mustexist=True,
                                             title="Dossier où enregistrer l'export")
        finally:
            root.destroy()
        return chosen or None
    except Exception:
        pass
    if sys.stdin is None or not sys.stdin.isatty():
        return None
    raw = input("Dossier où enregistrer l'export : ").strip().strip('"')
    return raw or None


def _title(args, saveas, proto):
    if args.title:
        return args.title
    name = str((saveas or {}).get("name") or "").strip()
    if name.lower().endswith(".figcraft"):
        name = name[: -len(".figcraft")].strip()
    return name or proto.get("title") or "Prototype"


def _digest_after(ctl, before):
    try:
        return docfile.digest(ctl.execute("file.saveAs", {"data": True})) == before
    except Exception:
        return False


def _render_failure(e, args):
    if isinstance(e, render.RenderError):
        lines = [str(e)]
        if e.remaining:
            lines.append(summary.steps_left(len(e.remaining)))
        return lines
    if isinstance(e, ControlError):
        return ["FigCraft a refusé la commande : %s" % e]
    if isinstance(e, KeyboardInterrupt):
        return ["Interrompu."]
    if args.debug:
        raise e
    return ["Erreur pendant le rendu : %s" % e]


def _export(ctl, args):
    _say("Lecture de la sélection...")
    try:
        before = ctl.execute("file.saveAs", {"data": True})
        d0 = docfile.digest(before)
        w = walk.walk(ctl, docfile.extras(before))
    except (walk.WalkError, docfile.DocFileError) as e:
        return _fail(str(e))
    proto = w["proto"]
    proto["title"] = _title(args, before, proto)
    v = variables.parse(w["variables_raw"])
    variables.add_jobs(w, v, variables.reachable(v, w["actions"]))
    _say(NO_TOUCH)
    _say("Rendu de %d écran(s), %d calque(s) au moins..." % (len(proto["screens"]), len(w["jobs"])))
    failure = None
    try:
        assets = render.render_all(ctl, w, scale=args.scale)
    except BaseException as e:   # every temporary edit was already undone (or reported)
        failure = e
    digest_ok = _digest_after(ctl, d0)
    if failure is not None:
        lines = _render_failure(failure, args) + [NOTHING_WRITTEN]
        lines.append(summary.DIGEST_OK if digest_ok else summary.DIGEST_WARNING)
        return _fail("\n".join(lines))
    folder = args.out or _ask_folder()
    if not folder:
        return _fail("Aucun dossier choisi : export annulé. " + NOTHING_WRITTEN)
    try:
        out = Path(folder).expanduser()
        out.mkdir(parents=True, exist_ok=True)
        target = writer.write(out, proto, assets, player_root())
    except writer.WriteError as e:
        return _fail(str(e))
    except OSError as e:
        return _fail("Impossible d'écrire l'export : %s\n%s" % (e, NOTHING_WRITTEN))
    _say(summary.text(proto, assets, w["warnings"], digest_ok, target))
    if not args.no_open:
        try:
            webbrowser.open((target / "index.html").resolve().as_uri())
        except Exception:
            _say("Ouvrez « %s » dans votre navigateur." % (target / "index.html"))
    return 0


def build_parser():
    p = argparse.ArgumentParser(prog="figcraft_export")
    sub = p.add_subparsers(dest="cmd")
    p.add_argument("--debug", action="store_true", help=argparse.SUPPRESS)
    pl = sub.add_parser("launch", help="démarre FigCraft")
    pl.add_argument("--port", type=int, default=DEFAULT_PORT)
    pl.add_argument("file", nargs="?")
    pe = sub.add_parser("export", help="exporte les cadres sélectionnés")
    pe.add_argument("--port", type=int, default=DEFAULT_PORT)
    pe.add_argument("--out")
    pe.add_argument("--scale", type=float, default=2)
    pe.add_argument("--no-open", action="store_true")
    pe.add_argument("--title")
    return p


def main(argv=None):
    _setup_console()
    parser = build_parser()
    argv = list(sys.argv[1:] if argv is None else argv)
    debug = "--debug" in argv
    if debug:
        argv.remove("--debug")
    try:
        args = parser.parse_args(argv)
        args.debug = debug
    except SystemExit as e:
        return 2 if e.code else 0
    if args.cmd is None:
        parser.print_usage(sys.stderr)
        return 2
    try:
        return cmd_launch(args) if args.cmd == "launch" else cmd_export(args)
    except ControlError as e:
        return _fail("FigCraft a refusé la commande : %s" % e)
    except KeyboardInterrupt:
        return _fail("Interrompu.")
    except OSError as e:
        return _fail("Erreur : %s" % e)
    except Exception as e:
        if getattr(args, "debug", False):
            raise
        return _fail("Erreur inattendue : %s" % e)


if __name__ == "__main__":
    sys.exit(main())
