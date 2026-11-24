# FigCraft → site HTML autonome : conception

Date : 2026-11-24 · Statut : relu, en attente de validation

## Intention

Dans FigCraft (https://getartcraft.com/apps/figcraft, v0.18, alpha), l'utilisateur sélectionne des
frames et lance un plugin. Le plugin produit un **prototype cliquable fidèle** : un dossier
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

## Contraintes (vérifiées dans `docs/plugins.md` de FigCraft)

- Plugin **WebAssembly** exécuté par wasmi. Pas de WASI : pas de fichiers, pas de réseau, pas
  d'horloge, pas d'aléatoire. Accès au document uniquement via `call(command, params)`, avec les
  mêmes commandes que le CLI et le serveur MCP.
- Le plugin **ne peut pas écrire un dossier**. Avec l'API 4 et `permissions.saveFile`, il peut
  proposer **un seul fichier par exécution, de 16 Mo au plus**. FigCraft ouvre sa propre fenêtre
  d'enregistrement.
- Limites par exécution : 1 000 000 000 de fuel (une instruction coûte environ 1 fuel, chaque
  octet copié depuis ou vers l'hôte coûte 1 fuel, chaque appel hôte 10 000 fuel), 64 Mo de
  mémoire, 100 000 appels hôte, 16 Mo par chaîne.
- Commandes interdites : `file.*`, `app.*`, `plugin.*`, `widget.*`, `doc.*` (sauf `doc.list`),
  et toute commande qui ouvre une fenêtre.
- Le site exporté doit fonctionner en `file://`. Pas de `fetch` de JSON ni de modules ES chargés
  dynamiquement : les données sont embarquées dans un fichier `.js` classique.
- Machine de l'utilisateur : macOS, **ni Rust ni Node.js installés aujourd'hui**. Il faudra
  installer Rust (rustup + cible `wasm32-unknown-unknown`) pour compiler. Node reste facultatif.
- FigCraft est en alpha : les commandes et le format peuvent changer. On cible la version
  courante (≥ 0.18.1) et le manifeste annonce l'API nécessaire.

## Approches envisagées

| | Approche | Atouts | Limites |
|---|---|---|---|
| **A** ✅ | **Plugin FigCraft** (Rust → wasm) qui lit la sélection et produit une archive | Intégré à FigCraft (menu Plugins), lit la sélection directement, rendu par le moteur FigCraft | Bac à sable : un seul fichier de 16 Mo par exécution, budget d'instructions, pas d'horloge |
| B | Outil Node qui lit le `.figcraft` enregistré | Contrôle total, automatisable | Ignore la sélection, dépend du format interne qui peut changer pendant l'alpha |
| C | Outil Node qui pilote FigCraft ouvert (port de contrôle ou MCP) | Sélection en direct, écrit un vrai dossier | Se lance depuis un terminal, nécessite Node |

**Choisie : A** (choix de l'utilisateur). C était ma recommandation, pour la liberté d'écriture.
A a été retenue en connaissance de cause, une fois confirmé que `save_file` permettait de livrer
une archive.

## Conception

### Vue d'ensemble

```
FigCraft ──(sélection)──▶ plugin wasm ──call()──▶ commandes FigCraft (node.get, export, variables…)
                              │
                              ├─ construit le modèle du prototype (JSON)
                              ├─ récupère les rendus (SVG / PNG) des calques
                              ├─ ajoute le lecteur JS/CSS (embarqué dans le module)
                              └─ save_file("<nom>.zip") ──▶ fenêtre d'enregistrement de FigCraft
```

Décompressée, l'archive donne :

```
<nom>/
  index.html        coquille : panneau latéral + scène
  player.js         lecteur générique (écrit à la main, identique pour tous les exports)
  player.css
  data.js           window.FIGCRAFT_PROTOTYPE = { … } : arbre, interactions, variables, réglages
  assets/           rendus SVG / PNG / JPEG, nommés par identifiant de calque (+ variante)
```

### Le plugin

- Manifeste `figcraft-plugin.json` : `api: 4` (minimum pour `saveFile`), `permissions.access:
  "read"`, `permissions.saveFile: true`, un `commands` « Exporter en site HTML… ». Les éventuels
  paramètres sont à décider par le constructeur (nom du site, échelle des PNG).
- Rust avec le crate `figcraft-plugin-sdk` (dans `plugins/sdk` du dépôt FigCraft), compilé en
  `cdylib` pour `wasm32-unknown-unknown`.
- Lecture du document : pour chaque frame sélectionnée, parcourir l'arbre (`node.get` avec
  profondeur et champs) afin de récupérer, par calque, la géométrie, la visibilité, le découpage
  (clip), le défilement (overflow), les calques fixes et sticky, les interactions, les
  liaisons de variables et, pour les instances, le composant, la variante et ses propriétés.
  Récupérer aussi les collections de variables et leurs modes, ainsi que les réglages de
  prototype de la page (`proto.settings {}`).
- **Fermeture transitive** : les frames sélectionnées sont les écrans du panneau latéral. Les
  frames et composants qu'elles atteignent (destinations Navigate et overlays, toutes les
  variantes des ensembles de composants utilisés par Change to) sont aussi exportés, sinon le
  prototype casserait. Voir « Choix faits à la relecture ».
- Les ressources du lecteur (`index.html`, `player.js`, `player.css`) sont embarquées dans le
  module au moment de la compilation (`include_bytes!`).
- Archive : un zip écrit à la main dans le plugin, en mode *stored* ou avec un deflate léger.
  Le constructeur choisit, selon le budget de fuel. Si l'archive dépasse 16 Mo, l'exécution
  échoue avec un message clair (taille obtenue, pistes : moins de frames, PNG à une échelle plus
  faible).
- Retour à l'utilisateur via `notify` : nombre d'écrans, taille de l'archive, éléments non
  supportés ou approximés.

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

- Logique Rust (parcours, modèle, zip) : tests unitaires `cargo test` hors wasm, où le SDK fait
  échouer les appels hôte.
- Lecteur : tests sur un `data.js` de démonstration (écrit à la main) qui couvre chaque
  déclencheur, chaque action et chaque transition. Les règles de `prototyping-parity.md` servent de
  liste de cas.
- Bout en bout : exporter les exemples du dépôt FigCraft (`examples/ridgeline-onboarding.figcraft`,
  `examples/ridgeline-design-system.figcraft`) et comparer, à l'œil puis par captures, au
  présentateur de FigCraft.

## Points à vérifier en premier (petit test jetable au démarrage)

La doc lue ne les confirme pas. Ils peuvent changer la conception :

1. Le nom exact de la commande d'export accessible à un plugin, et le fait qu'elle renvoie bien
   les octets sans `path` (le serveur MCP le fait avec `export`).
2. Ce que `node.get` renvoie pour les interactions, les liaisons de variables, l'overflow et les
   calques fixes.
3. Le moyen de rendre un conteneur **sans ses enfants**.
4. Le budget de fuel sur un vrai fichier : nombre d'appels, octets copiés, compression.

Si (1) ou (3) échoue, le repli est de rendre les frames d'un bloc, ce qui fait perdre la précision
de Smart Animate. Il faudra en reparler avec l'utilisateur.

## Laissé au constructeur

- L'organisation du code Rust et JS, et les noms de fichiers des ressources.
- Les paramètres de la commande du plugin.
- Le format de rendu par type de calque et l'échelle des PNG (2x par défaut).
- La compression du zip.
- L'apparence exacte du panneau latéral, dans l'esprit de la maquette A.

## Choix faits à la relecture (décisions de Claude, à vérifier par l'utilisateur)

- **Portée de l'export** : la sélection de la page courante. Le panneau latéral liste les frames
  sélectionnées, groupées par section (la page n'est qu'un titre).
- **Premier écran et « redémarrer »** : le point de départ du flow de la page s'il fait partie
  de la sélection, sinon la première frame sélectionnée dans l'ordre des calques.
- **Fermeture transitive** : on suit tous les liens (Navigate, overlays, Change to), à toutes les
  profondeurs et sur toutes les pages. Les frames atteintes mais non sélectionnées sont exportées
  sans apparaître dans le panneau. Au-delà de 16 Mo, l'export échoue avec un message qui donne la
  taille et ce qui pèse le plus. On ne coupe jamais de lien en silence.

## Décisions de l'utilisateur (après relecture)

1. **Variables en direct : option a.** La visibilité, les textes et les nombres liés à des
   variables sont mis à jour en direct par le lecteur. Les **couleurs liées** et les **changements
   de mode** (Set variable mode, clair/sombre…) sont **pré-rendus** pour chaque valeur ou mode
   *réellement atteignable* par les actions du prototype, et le lecteur échange les rendus. Le
   plugin calcule les valeurs atteignables à partir des actions Set variable et Set variable mode.
   Une valeur calculée par une expression dont l'ensemble n'est pas fini est signalée comme
   approximée dans le `notify`. Ce pré-rendu est la principale cause de grossissement de
   l'archive : il fait partie du message d'erreur si l'archive dépasse 16 Mo.
2. **Effets qui dépendent de l'arrière-plan : option b, l'animation l'emporte.** Le découpage
   calque par calque est conservé partout. Le flou d'arrière-plan, le verre, les modes de fusion,
   les masques et les découpes non rectangulaires sont reproduits en CSS (`backdrop-filter`,
   `mix-blend-mode`, `mask`/`clip-path`). Le calque est alors rendu sans cet effet, et c'est le
   CSS qui l'applique. Un léger écart de rendu est accepté pour ces seuls effets : c'est une
   exception explicite à l'anti-objectif de fidélité. Le `notify` de fin d'export liste les
   calques concernés.
