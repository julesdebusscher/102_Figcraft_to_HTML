"""Build dist/FigCraft Export HTML/: the four launchers, figcraft_export/ (no tests, no
caches, no config) with the player prebuilt in figcraft_export/player/, and LISEZMOI.txt.

    python3 tools/make_dist.py [--out <dir>]      (default: <repo>/dist)
"""
import argparse
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
EXPORTER = ROOT / "exporter"
PLAYER = ROOT / "player"
NAME = "FigCraft Export HTML"
LAUNCHERS = ("Ouvrir FigCraft.bat", "Exporter la sélection.bat",
             "Ouvrir FigCraft.command", "Exporter la sélection.command")

LISEZMOI = """FigCraft Export HTML
====================

Exporte des écrans FigCraft en un prototype HTML autonome : un dossier qui s'ouvre
par double-clic dans Chrome, Edge ou Firefox, sans connexion ni serveur.

1. Installer Python (une seule fois)
------------------------------------
- Windows : téléchargez Python 3 sur https://www.python.org/downloads/ (version 3.8
  ou plus récente) et, pendant l'installation, cochez « Add python.exe to PATH ».
  Rien d'autre à installer.
- Mac : Python 3 est souvent déjà présent ; sinon, installez-le depuis python.org.

2. Exporter, dans cet ordre
---------------------------
1. Fermez FigCraft s'il est ouvert.
2. Double-cliquez sur « Ouvrir FigCraft » (.bat sous Windows, .command sur Mac) :
   FigCraft démarre, prêt à être piloté par l'export. Ouvrez votre fichier.
3. Dans FigCraft, sélectionnez les frames de premier niveau à exporter
   (Maj+clic pour en choisir plusieurs), ou une section entière. Les écrans
   reliés par des interactions sont ajoutés automatiquement.
4. Double-cliquez sur « Exporter la sélection ».
   Ensuite, ne touchez pas à FigCraft pendant l'export (de quelques secondes à
   quelques minutes selon la taille du fichier) : l'outil modifie temporairement
   le document pour rendre chaque calque, puis annule tout.
5. Choisissez le dossier de destination. Le prototype s'ouvre dans le navigateur.
   Pour le partager, envoyez le dossier entier (index.html, player.js, player.css,
   data.js et assets/), par exemple en archive .zip.

3. En cas de problème
---------------------
- « Python 3.8 ou plus récent est introuvable » : installez Python (étape 1), puis
  rouvrez la fenêtre.
- « Impossible de joindre FigCraft » : FigCraft a été ouvert autrement que par
  « Ouvrir FigCraft ». Fermez-le et relancez-le avec « Ouvrir FigCraft ».
- « FigCraft est introuvable » : indiquez le chemin de FigCraft.exe quand il est
  demandé ; il est retenu dans config.json, à côté de ce fichier.
- « Sélectionnez au moins une frame de premier niveau » : sélectionnez une frame
  posée directement sur la page (pas un calque à l'intérieur d'une frame).
- « Attention : le document FigCraft a peut-être été modifié » ou « modifications
  temporaires restent dans l'historique » : quelque chose a changé pendant l'export.
  Utilisez Cmd/Ctrl+Z dans FigCraft comme indiqué, vérifiez le document, puis
  relancez l'export sans toucher à FigCraft.
- « Le dossier ... ne contient pas un export » : un dossier du même nom existe déjà ;
  choisissez une autre destination. Un export précédent du même prototype, lui,
  est remplacé.
- Le rapport affiché en fin d'export liste les effets approximés et les éléments
  ignorés.
"""


def _ignore(directory, names):
    return [n for n in names if n == "__pycache__" or n.endswith((".pyc", ".pyo")) or n == "config.json"
            or n.startswith(".")]


def build(out_dir):
    sys.path.insert(0, str(EXPORTER))
    from figcraft_export import writer

    dest = Path(out_dir) / NAME
    if dest.exists():
        shutil.rmtree(str(dest))
    dest.mkdir(parents=True)
    for name in LAUNCHERS:
        shutil.copy2(str(EXPORTER / name), str(dest / name))
    pkg = dest / "figcraft_export"
    shutil.copytree(str(EXPORTER / "figcraft_export"), str(pkg), ignore=_ignore)
    player = pkg / "player"
    player.mkdir()
    shutil.copy2(str(PLAYER / "index.html"), str(player / "index.html"))
    shutil.copy2(str(PLAYER / "player.css"), str(player / "player.css"))
    with open(str(player / "player.js"), "wb") as f:
        f.write(writer.player_js(PLAYER).encode("utf-8"))
    with open(str(dest / "LISEZMOI.txt"), "wb") as f:   # BOM + CRLF: Notepad shows the accents
        f.write(b"\xef\xbb\xbf" + LISEZMOI.replace("\n", "\r\n").encode("utf-8"))
    return dest


def main(argv=None):
    p = argparse.ArgumentParser(prog="make_dist")
    p.add_argument("--out", default=str(ROOT / "dist"))
    args = p.parse_args(argv)
    dest = build(args.out)
    print("Distribution : %s" % dest)
    return 0


if __name__ == "__main__":
    sys.exit(main())
