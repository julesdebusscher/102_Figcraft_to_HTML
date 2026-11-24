# FigCraft → site HTML autonome : conception

Date : 2026-11-24 · Statut : validé, révisé le 2026-11-24 après le test de l'API (outil Python au lieu d'un plugin)

## Intention

Dans FigCraft (https://getartcraft.com/apps/figcraft, v0.18, alpha), l'utilisateur sélectionne des
frames et lance l'export. L'outil produit un **prototype cliquable fidèle** : un dossier
`index.html` + JS + CSS + ressources qui s'ouvre dans n'importe quel navigateur, sans serveur
(`file://`), et rejoue les interactions prototypées dans FigCraft.

Le prototype servira dans « un environnement plus large ». Pour l'instant, il y est rangé ou
ouvert tel quel, sans que son code soit mélangé à celui d'une autre application.

## Objectifs

- Partir de la **sélection courante** (frames de premier niveau) dans FigCraft.
- **Fidélité visuelle** au rendu de FigCraft : le rendu vient du moteur de FigCraft, pas d'une
  reconstruction CSS.
- **Toutes les interactions** du prototypage FigCraft (« niveau 3 ») :
  - déclencheurs : On click, On hover (while hovering), On press (while pressing), On drag,
    Mouse enter / leave / down / up (avec `delayMs`), After delay, Key press (touches et
    combinaisons ; les boutons de manette sont un bonus) ;
  - actions : Navigate (avec `preserveScroll`), Back, Scroll to (avec `offset`), Open / Swap / Close
    overlay (positions, `anchor`, `offset`, fond assombri, fermeture au clic extérieur), Open URL,
    Change to (variantes), Set variable (valeur ou expression), Set variable mode, Conditional ;
  - transitions : les 8 (Instant, Dissolve, Smart Animate, Move in/out, Push, Slide in/out) et les
    13 courbes d'easing (y compris bezier et ressorts physiques) ;
  - composants interactifs : chaque instance joue les interactions de la variante affichée, une
    interaction propre à l'instance sur le même déclencheur l'emporte ;
  - défilement : frames qui défilent, calques fixes et sticky, défilement préservé ;
  - historique : Back ferme d'abord l'overlay du dessus, sinon revient à l'écran précédent en
    jouant l'animation à l'envers ; redémarrer vide l'historique.
  La référence de comportement est `docs/prototyping-parity.md` du dépôt FigCraft : le site doit
  se comporter comme le présentateur de FigCraft.
- **Navigation entre frames** par un **panneau latéral** repliable qui liste les frames exportées,
  groupées par page puis par section FigCraft, et met en évidence la frame affichée. Un bouton
  « redémarrer » est disponible (maquette validée : option A de
  `.superpowers/brainstorm/navigation.html`).
- Le prototype s'adapte à la fenêtre comme le présentateur : la frame est mise à l'échelle pour
  tenir, et une frame plus haute que l'écran défile.

## Hors objectifs

- Un HTML/CSS propre, sémantique, responsive ou retouchable à la main.
- L'intégration dans le code d'une autre application (isolation des styles, API de pilotage). Plus
  tard peut-être, mais rien dans cette version.
- L'hébergement ou un serveur.
- Les déclencheurs et actions média (FigCraft ne les gère pas non plus), les commentaires, le mode
  Inspect et les cadres d'appareil.

## Anti-objectifs (échec même si « ça marche »)

- Un rendu visiblement différent de FigCraft (polices, ombres, flous, dégradés), hors effets dépendant de l'arrière-plan approximés en CSS (voir Décisions).
- Un site qui exige un serveur local ou Internet pour s'ouvrir.
- Des interactions qui se comportent autrement que dans le présentateur de FigCraft.

## Contraintes

- **Poste cible : Windows, avec Python 3 et FigCraft seulement.** L'outil n'utilise que la
  bibliothèque standard de Python (≥ 3.8), sans `pip install`. Le site produit n'a besoin que d'un
  navigateur. Le moteur JS de macOS (`jsc`) ne sert qu'aux tests du lecteur, en développement.
- Le test de l'API (2026-11-24, `docs/figcraft-api-notes.md`) a montré qu'**un plugin FigCraft ne
  peut pas obtenir de rendu** : toutes les commandes d'export sont `file.*`, refusées aux plugins.
  Le rendu passe donc par le **canal de contrôle** de FigCraft (`--control <port>`, JSON par ligne
  sur `127.0.0.1`), où `file.export` renvoie le SVG ou le PNG en base64.
- Le canal de contrôle n'existe que si FigCraft a été lancé avec `--control <port>` : on l'ouvre
  par un lanceur.
- `node.get` ne donne ni le défilement (overflow), ni les calques fixes ou sticky, ni les modes de
  variables. `file.saveAs {data:true}` (contrôle) renvoie le fichier, dont `document.json` contient
  `overflow`, `scroll_position` et `var_modes`.
- Les modifications temporaires (masquer des enfants, changer de variante ou de mode) sont
  restaurées : test du 2026-11-24, `document.json` identique octet pour octet après restauration.
- Le site exporté doit fonctionner en `file://` : pas de `fetch` de JSON ni de modules ES chargés
  dynamiquement, les données sont embarquées dans un fichier `.js` classique.
- FigCraft est en alpha : les commandes et le format peuvent changer. On cible la version
  ≥ 0.18.1 et l'outil vérifie la version au démarrage.

## Approches envisagées

| | Approche | Atouts | Limites |
|---|---|---|---|
| A | Plugin FigCraft (Rust → wasm) | Intégré au menu Plugins, lit la sélection | **Impossible** : pas de rendu accessible aux plugins (test du 2026-11-24) |
| B | Outil qui lit le `.figcraft` enregistré | Contrôle total | Ignore la sélection, dépend du format interne, pas de rendu |
| **C** ✅ | **Outil Python qui pilote FigCraft ouvert** par son canal de contrôle | Sélection en direct, rendu par le moteur FigCraft, accès à tout le document, écrit un vrai dossier | FigCraft doit être ouvert par le lanceur ; l'export se lance par un double-clic, pas depuis le menu Plugins |

**Choisie d'abord : A** (choix de l'utilisateur), **puis C** après l'échec du test de l'API (choix
de l'utilisateur, 2026-11-24), en **Python** parce que le poste cible n'a que Python.

## Conception

### Vue d'ensemble

```
Ouvrir FigCraft.bat ──▶ FigCraft --control <port>
                            ▲
Exporter la sélection.bat ──┤ JSON par ligne sur 127.0.0.1
  (python figcraft_export)  │  sélection, node.get, variable.list, file.saveAs {data}, file.export…
                            │
                            ├─ construit le modèle du prototype (JSON)
                            ├─ récupère les rendus (SVG / PNG) des calques
                            ├─ copie le lecteur JS/CSS
                            └─ écrit le dossier choisi (fenêtre de choix de dossier), puis l'ouvre
                               dans le navigateur
```

Le dossier exporté :

```
<nom>/
  index.html        coquille : panneau latéral + scène
  player.js         lecteur générique (écrit à la main, identique pour tous les exports)
  player.css
  data.js           window.FIGCRAFT_PROTOTYPE = { … } : arbre, interactions, variables, réglages
  assets/           rendus SVG / PNG / JPEG, nommés par identifiant de calque (+ variante)
```

### L'outil d'export (Python)

- Livré comme un dossier `FigCraft Export HTML/` à copier sur le poste : deux lanceurs Windows
  (`Ouvrir FigCraft.bat`, `Exporter la sélection.bat`), le paquet Python `figcraft_export/` et le
  lecteur. Des lanceurs `.command` équivalents existent pour macOS (développement).
- `Ouvrir FigCraft` trouve `FigCraft.exe` dans les emplacements d'installation habituels, sinon
  demande son chemin une fois et le retient dans `config.json` à côté de l'outil, puis le lance
  avec `--control <port>`.
- `Exporter la sélection` se connecte, vérifie la version, lit la page courante et la sélection,
  parcourt les frames (`node.get`), lit `document.json` via `file.saveAs {data:true}` pour le
  défilement, les calques fixes et les modes, et lit les variables (`variable.list`) ainsi que les
  flows de la page. Il calcule la **fermeture transitive** (voir « Choix faits à la relecture »),
  rend chaque calque, écrit le dossier et affiche un résumé en français dans la console (nombre
  d'écrans, taille, éléments approximés ou ignorés). Il ouvre ensuite `index.html`.
- Le dossier de destination est choisi par une fenêtre `tkinter`. Si `tkinter` est absent, le
  chemin est demandé dans la console.
- Plus de limite de 16 Mo ni d'archive : le dossier est écrit directement.
- Pas de paramètres obligatoires. Le titre vient du nom du fichier ou de la page, l'échelle des
  PNG vaut 2 (option en ligne de commande).
- Toute modification temporaire faite pour le rendu est restaurée, même en cas d'erreur.

### Rendu (fidélité + animations)

Pour que Smart Animate, les variantes, le défilement et les calques fixes fonctionnent, on ne rend
pas une image par frame. Le site reconstruit l'**arbre des calques en éléments HTML
positionnés en absolu**, chacun portant sa transformation, son opacité et son découpage :

- les **conteneurs** (frames, groupes, instances) deviennent des `div` positionnées, avec
  découpage, défilement et calques fixes. Leur propre peinture (fond, bordure, ombre, flou) est
  rendue par FigCraft en image, *sans leurs enfants* (`contentsOnly`, ou un équivalent à
  trouver) ;
- les **feuilles** (vecteurs, formes, textes, images) sont rendues par la commande d'export de
  FigCraft : SVG par défaut, PNG ou JPEG pour les images bitmap et les effets que le SVG rendrait
  mal (bruit, flou de calque ; le flou d'arrière-plan et le verre passent par le CSS, voir décision 2). Le choix de format par calque revient au constructeur ;
- **textes** : rendus en SVG avec le texte vectorisé (fidélité sans dépendre des polices du
  visiteur). Exception : un texte lié à une variable texte ou nombre devient un vrai texte HTML,
  mis à jour par le lecteur. Pour ces textes, le lecteur applique la police, la taille, la
  graisse et la couleur relevées dans FigCraft, et reste tributaire des polices installées
  (limite connue) ;
- **Smart Animate** : les calques de l'écran de départ et de l'écran d'arrivée sont appariés par
  nom et hiérarchie, comme le fait FigCraft. Position, taille, rotation et opacité sont
  interpolées. Les calques sans correspondance apparaissent ou disparaissent en fondu ;
- les **variantes** sont rendues chacune comme un sous-arbre, et Change to remplace un sous-arbre
  par un autre avec la transition demandée.

### Le lecteur (`player.js`)

JS sans dépendance ni étape de compilation, écrit une fois et livré tel quel. Il :

- construit le DOM à partir de `data.js`, met la frame courante à l'échelle de la fenêtre et gère
  le défilement ;
- branche les déclencheurs (pointeur, clavier, manette via l'API Gamepad, minuteurs) avec les
  règles de priorité de FigCraft : le calque le plus haut l'emporte, un calque sans ce
  déclencheur laisse passer l'événement, et les calques masqués ne réagissent pas ;
- exécute les actions, gère la pile d'overlays et l'historique ;
- évalue les variables et les expressions (`add`, `subtract`, `multiply`, `divide`, comparaisons,
  etc.), les conditions et les modes de collection. Les liaisons de variables qui changent le rendu
  (couleur, visibilité, texte, mode) sont appliquées en direct selon la décision 1 (voir
  « Décisions de l'utilisateur ») ;
- joue les transitions et les courbes d'easing, y compris les ressorts physiques ;
- affiche le panneau latéral (pages → sections → frames), repliable, avec la frame courante en
  surbrillance et un bouton redémarrer.

### Tests

- Logique Python (parcours, modèle, variables, rendu, écriture) : `unittest` de la bibliothèque
  standard, avec un faux canal de contrôle qui rejoue des réponses enregistrées.
- Spécificités Windows (chemins avec espaces et accents, encodage UTF-8 des fichiers et de la
  console, lanceurs `.bat`) : tests unitaires quand c'est possible, puis une liste de vérifications
  à faire par l'utilisateur sur le poste Windows.
- Lecteur : tests sur un `data.js` de démonstration (écrit à la main) qui couvre chaque
  déclencheur, chaque action et chaque transition. Les règles de `prototyping-parity.md` servent de
  liste de cas.
- Bout en bout : exporter les exemples du dépôt FigCraft (`examples/ridgeline-onboarding.figcraft`,
  `examples/ridgeline-design-system.figcraft`) et comparer, à l'œil puis par captures, au
  présentateur de FigCraft.

## Résultats du test de l'API (2026-11-24)

Détail dans `docs/figcraft-api-notes.md`. Rendu impossible depuis un plugin, d'où le passage à
l'outil Python. Par le canal de contrôle : `file.export` renvoie `{format, data}` en base64. Un
conteneur se rend sans ses enfants en les masquant puis en les réaffichant. Les changements
temporaires de variante et de mode se restaurent sans trace dans `document.json`.

## Laissé au constructeur

- L'organisation du code Python et JS, et les noms de fichiers des ressources.
- Le port du canal de contrôle et les options de la ligne de commande.
- Le format de rendu par type de calque et l'échelle des PNG (2x par défaut).
- L'apparence exacte du panneau latéral, dans l'esprit de la maquette A.

## Choix faits à la relecture (décisions de Claude, à vérifier par l'utilisateur)

- **Portée de l'export** : la sélection de la page courante. Le panneau latéral liste les frames
  sélectionnées, groupées par section (la page n'est qu'un titre).
- **Premier écran et « redémarrer »** : le point de départ du flow de la page s'il fait partie
  de la sélection, sinon la première frame sélectionnée dans l'ordre des calques.
- **Fermeture transitive** : on suit tous les liens (Navigate, overlays, Change to), à toutes les
  profondeurs et sur toutes les pages. Les frames atteintes mais non sélectionnées sont exportées
  sans apparaître dans le panneau. Un lien vers une frame introuvable est signalé dans le résumé,
  jamais coupé en silence.

## Décisions de l'utilisateur (après relecture)

1. **Variables en direct : option a.** La visibilité, les textes et les nombres liés à des
   variables sont mis à jour en direct par le lecteur. Les **couleurs liées** et les **changements
   de mode** (Set variable mode, clair/sombre…) sont **pré-rendus** pour chaque valeur ou mode
   *réellement atteignable* par les actions du prototype, et le lecteur échange les rendus. Le
   l'outil calcule les valeurs atteignables à partir des actions Set variable et Set variable mode.
   Une valeur calculée par une expression dont l'ensemble n'est pas fini est signalée comme
   approximée dans le résumé de fin d'export. Ce pré-rendu est la principale cause de
   grossissement du dossier : le résumé donne sa taille.
2. **Effets qui dépendent de l'arrière-plan : option b, l'animation l'emporte.** Le découpage
   calque par calque est conservé partout. Le flou d'arrière-plan, le verre, les modes de fusion,
   les masques et les découpes non rectangulaires sont reproduits en CSS (`backdrop-filter`,
   `mix-blend-mode`, `mask`/`clip-path`). Le calque est alors rendu sans cet effet, et c'est le
   CSS qui l'applique. Un léger écart de rendu est accepté pour ces seuls effets : c'est une
   exception explicite à l'anti-objectif de fidélité. Le résumé de fin d'export liste les
   calques concernés.
