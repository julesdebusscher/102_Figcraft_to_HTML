# FigCraft vers HTML

Exporte des écrans FigCraft en **prototype HTML autonome** : un dossier (`index.html`, `player.js`,
`player.css`, `data.js`, `assets/`) qui s'ouvre par double-clic dans Chrome, Edge ou Firefox, sans
serveur ni connexion. Les interactions du prototype FigCraft (navigation, retour, survol, clic, délais,
superpositions, changements de variante, variables, défilement, liens) sont rejouées par un petit
lecteur JavaScript.

L'export pilote FigCraft par son canal de contrôle local (`--control`), rend chaque calque en SVG/PNG
en modifiant temporairement le document, puis annule tout et vérifie que le document est inchangé.

## Prérequis

- Python 3.8 ou plus récent (bibliothèque standard uniquement, rien à installer avec pip).
- FigCraft 0.18.1 ou plus récent (Mac ou Windows).

## Installation

Copiez le dossier `dist/FigCraft Export HTML/` où vous voulez (Bureau, Documents...). Il se génère avec
`python3 tools/make_dist.py`. Il contient les lanceurs `.bat` (Windows) et `.command` (Mac), le paquet
`figcraft_export/` avec le lecteur déjà construit, et `LISEZMOI.txt`.

## Utilisation

1. Fermez FigCraft s'il est ouvert.
2. Double-cliquez sur **Ouvrir FigCraft** : FigCraft démarre en mode contrôlé. Ouvrez votre fichier.
3. Sélectionnez les frames de premier niveau à exporter (Maj+clic pour plusieurs). Les écrans reliés
   par des interactions sont ajoutés automatiquement.
4. Double-cliquez sur **Exporter la sélection**. Ne touchez pas à FigCraft pendant l'export.
5. Choisissez le dossier de destination : le prototype s'ouvre dans le navigateur. Pour le partager,
   envoyez le dossier entier (par exemple en .zip).

Ligne de commande équivalente : `python3 -m figcraft_export launch [fichier]` puis
`python3 -m figcraft_export export [--port N] [--out dossier] [--scale 2] [--no-open] [--title ...]`.

## Ce qui est pris en charge

Frames de premier niveau (et frames dans des sections), auto-layout, textes, formes, vecteurs, images,
masques, effets, composants et variantes (dont changements de variante interactifs), variables et modes
(changement de mode, variables numériques/booléennes/couleur, conditions), interactions : navigation,
retour, superpositions, défilement vers un calque, liens, minuteries, survol/clic/appui/touche, et
transitions (instantané, dissolution, déplacement, glissement, Smart Animate) avec courbes et ressorts.

## Limites connues

- **Approximations CSS** : flou d'arrière-plan et effet verre (rendus en flou d'arrière-plan CSS), flou de
  calque, modes de fusion et masques sont approchés en CSS. Ils sont listés sous « Rendu approximé » dans
  le résumé de fin d'export.
- **Les dégradés sont exportés en PNG** (leur angle diffère en SVG sur les calques non carrés) : le dossier
  est plus lourd (l'exemple d'onboarding passe d'environ 0,26 Mo à 0,97 Mo).
- **Superpositions** : les décalages des positions prédéfinies (hors position manuelle) et l'avis
  « Ouvrir le lien » que FigCraft affiche ne sont pas reproduits (les liens s'ouvrent directement).
- **Masques de luminance** : tout masque est rendu comme un masque alpha, et appliqué à tout son groupe.
- **Variantes de tailles différentes** : l'instance garde la taille de la variante courante ; une variante
  d'une autre taille ne s'affiche correctement que si l'instance ne rogne pas son contenu.
- **Ne touchez pas à FigCraft pendant l'export** (5 à 15 secondes) : l'outil modifie temporairement le
  document puis annule ses modifications. Si vous modifiez quelque chose entre-temps, le résumé affiche un
  avertissement et indique quoi annuler (Cmd/Ctrl+Z).
- **Le document apparaît comme modifié** dans FigCraft après l'export (les modifications et leur annulation
  marquent le document) ; son contenu est identique, ce que le résumé confirme (« inchangé (vérifié) »).
  L'historique de rétablissement (Cmd/Ctrl+Maj+Z) est vidé.
- Les polices doivent être disponibles sur l'ordinateur qui ouvre le prototype pour le texte non rendu en
  image ; seules les frames de premier niveau sont exportées (les calques isolés sont ignorés et signalés).
- Sous Windows, `FigCraft.exe --version` n'a pas été vérifié : si rien n'est affiché, le contrôle de
  version est simplement ignoré.

## Dépannage

- **« Python 3 est introuvable »** : installez Python 3.8+ depuis python.org (Windows : cochez « Add
  python.exe to PATH »), puis rouvrez la fenêtre.
- **« Impossible de joindre FigCraft »** : FigCraft n'a pas été ouvert par « Ouvrir FigCraft ». Fermez-le
  complètement et relancez-le ainsi.
- **Port occupé** : un autre programme utilise le port 47917. Lancez avec un autre port :
  `python3 -m figcraft_export launch --port 47930` puis `python3 -m figcraft_export export --port 47930`.
- **« FigCraft est introuvable »** : indiquez le chemin de `FigCraft.exe` quand il est demandé ; il est
  retenu dans `figcraft_export/config.json` (`{"figcraft_path": "C:\\...\\FigCraft.exe"}`).
- **« Le dossier ... ne contient pas un export »** : un dossier du même nom existe déjà ; choisissez
  une autre destination.

## Pour les développeurs

- Lecteur (`player/`) : `bash player/test/run.sh`.
- Exporteur : `cd exporter && python3 -m unittest discover -s tests -t .`.
- Bout en bout (lance son propre FigCraft sur une copie de l'exemple, exporte, rend des PNG de référence
  à côté de l'export, dans `<out>/_reference/`, vérifie, puis quitte sans enregistrer) :
  `python3 tools/e2e.py examples/ridgeline-onboarding.figcraft [--frames "1 Welcome,3 Location"] [--out dossier] [--use-dist]`.
- Distribution : `python3 tools/make_dist.py` crée `dist/FigCraft Export HTML/`.
- Notes sur l'API de FigCraft : `docs/figcraft-api-notes.md`. Vérifications sous Windows :
  `docs/windows-checklist.md`.
