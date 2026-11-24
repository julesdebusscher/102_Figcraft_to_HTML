# Vérification sur Windows

À faire sur le PC Windows, dans l'ordre. Pour chaque étape, comparez avec le résultat attendu ; en cas
d'écart, notez le numéro de l'étape (voir « Si quelque chose échoue » en bas).

1. **Python.** Ouvrez l'invite de commandes et tapez `py -3 --version`.
   Attendu : `Python 3.8.x` ou plus récent. Sinon, installez Python depuis python.org en cochant
   « Add python.exe to PATH ».
2. **Copie.** Copiez le dossier `FigCraft Export HTML` (celui qui contient `Ouvrir FigCraft.bat`) sur le
   Bureau ou dans Documents.
   Attendu : on y voit 2 fichiers `.bat`, `LISEZMOI.txt`, et le dossier `figcraft_export`.
3. **Ouvrir FigCraft.** Fermez FigCraft, puis double-cliquez sur `Ouvrir FigCraft.bat`.
   Attendu : une fenêtre noire s'ouvre. Si FigCraft n'est pas trouvé automatiquement, elle demande le
   chemin de `FigCraft.exe` (collez-le, avec ou sans guillemets) ; il est ensuite retenu dans
   `figcraft_export\config.json`. Elle affiche « FigCraft démarre (port 47917)... » puis
   « FigCraft est prêt. » et FigCraft s'ouvre.
4. **Contrôle de version.** Notez ce que la fenêtre a affiché : rien de plus (version acceptée ou contrôle
   ignoré silencieusement) est normal ; un message « FigCraft x.y.z ou plus récent est nécessaire (trouvé :
   ...) » ne l'est que si votre FigCraft est plus ancien que 0.18.1. À noter dans votre retour, car
   `FigCraft.exe --version` n'a jamais été vérifié sous Windows. Vérifiez aussi qu'aucune fenêtre
   parasite ne s'est ouverte.
5. **Ouvrir un fichier.** Dans FigCraft, ouvrez un fichier `.figcraft` (par exemple
   `ridgeline-onboarding.figcraft`, dans `examples`).
6. **Sélection.** Sélectionnez 2 ou 3 frames de premier niveau (Maj+clic).
7. **Exporter.** Double-cliquez sur `Exporter la sélection.bat`.
   Attendu : « Lecture de la sélection... », « Ne modifiez pas le document dans FigCraft pendant
   l'export. », « Rendu de N écran(s)... » ; ne touchez pas à FigCraft. Puis une fenêtre « Dossier où
   enregistrer l'export » s'ouvre.
8. **Dossier avec espaces et accents.** Créez et choisissez `C:\Users\<votre nom>\Mes prototypes`.
   Attendu : le résumé est en français, sans caractères déformés (« écrans exportés », « inchangé
   (vérifié) », guillemets « »), avec le chemin complet du dossier. Il se termine par
   « Le document FigCraft est inchangé (vérifié). ». Le navigateur par défaut s'ouvre sur le prototype.
9. **Edge.** Fermez le navigateur, puis, dans l'Explorateur, ouvrez
   `C:\Users\<votre nom>\Mes prototypes\<nom-du-prototype>\index.html` par double-clic avec Edge
   (clic droit > Ouvrir avec > Microsoft Edge).
   Attendu : le premier écran s'affiche (adresse `file:///...`), mise en page et images correctes.
10. **Chrome.** Même chose avec Google Chrome.
11. **Parcours.** Cliquez dans le prototype : boutons de navigation, retour, survol, une superposition
    si le fichier en a une, texte et images nets.
    Attendu : comportement identique à celui du prototype dans FigCraft ; rien de cassé.
12. **Ré-export dans le même dossier.** Refaites les étapes 6 à 8 en choisissant le même dossier
    `Mes prototypes`.
    Attendu : l'export précédent est remplacé sans erreur (même nom de sous-dossier), le résumé est de
    nouveau en français et le prototype s'ouvre.
13. **FigCraft fermé.** Fermez FigCraft, puis double-cliquez sur `Exporter la sélection.bat`.
    Attendu : le message « Impossible de joindre FigCraft. Ouvrez-le avec « Ouvrir FigCraft ». » (aucun
    plantage, aucun fichier écrit), puis « Appuyez sur une touche » pour fermer.

## Si quelque chose échoue

Envoyez : (1) le numéro de l'étape, (2) le texte complet de la fenêtre noire (sélectionnez-le avec la
souris, clic droit pour copier, ou faites une capture d'écran), (3) une capture d'écran de FigCraft et,
pour un problème d'affichage, du navigateur et de la même frame dans FigCraft, (4) le résultat de
`py -3 --version` et la version de FigCraft (Aide > À propos).
