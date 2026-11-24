"""Command line: python -m figcraft_export launch|export."""
import argparse
import sys
from pathlib import Path

from . import MIN_VERSION, version_ok
from .control import DEFAULT_PORT, Control, ControlError, Unreachable
from . import launcher


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
        _say("Export : à venir.")
        return 0
    finally:
        control.close()


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
