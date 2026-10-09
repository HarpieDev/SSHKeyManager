# Harpie — mon gestionnaire de clés SSH

Application Windows pour **usage personnel uniquement**. Pas de publication,
de compte utilisateur ni de télémétrie.

## Lancement

Lancer `dist/Harpie.exe` par double-clic.
OpenSSH Windows est nécessaire pour les connexions et SSH Agent ; il n'est plus
nécessaire pour créer ou gérer les clés.

Depuis les sources (Python 3.10+ ; environnement testé : Python 3.14) :

```powershell
python -m venv .venv
.venv\Scripts\python.exe -m pip install -r requirements.txt
.venv\Scripts\python.exe main.py
```

## Fonctions

- Création Ed25519 ou RSA 4096, avec ou sans passphrase.
- Serveur optionnel, utilisateur et port SSH configurables.
- Recherche, tri par date réelle, tags et filtres.
- Page Tags : recherche, création, renommage, couleur personnalisée, aperçu et suppression confirmée.
- Aperçu de la clé sélectionnée ; détails par double-clic ou Entrée.
- Onglets pour l’identité, la connexion et les actions de sécurité.
- Vue « À vérifier » pour retrouver les clés présentant un avertissement.
- Import d'une clé privée OpenSSH ou PEM, y compris chiffrée ; validation du `.pub` associé.
- Export public ou privé, sans écrasement d'un fichier existant.
- Détection des clés orphelines, des paires incohérentes et des permissions trop ouvertes.
- Reconstruction d'un `.pub` manquant et correction des permissions du fichier privé.
- Vérification intégrale d'une clé et changement de sa passphrase sans commande.
- Ajout/retrait à SSH Agent ; visualisation des clés chargées depuis la barre latérale.
- Suppression récupérable depuis **Corbeille** dans la barre latérale.
- Connexion dans un terminal OpenSSH et accès aux réglages SSH de GitHub.
- Interface réactive, fenêtre redimensionnable, taille mémorisée.
- Fenêtre sans barre de titre séparée : contrôles intégrés, déplacement et redimensionnement Windows ; maximisation dans la zone disponible du moniteur.
- Interface inspirée des références Apple : fond noir, grandes cartes arrondies,
  capsules et palette bleu, violet, orange, rose et gris relevée dans les captures ;
  police Inter intégrée (aucune installation nécessaire).
- Résumé de la bibliothèque : nombre de clés, de clés privées avec passphrase et d'avertissements.
- Logo Harpie et icônes vectorielles ; icône Windows du `.exe` en neuf résolutions.

Raccourcis : **Ctrl+N** nouvelle clé, **Ctrl+F** recherche, **F5** actualiser.

La police [Inter 4.1](https://rsms.me/inter/) est fournie sous licence SIL OFL 1.1,
avec sa licence dans `assets/fonts/OFL.txt`. Le logo et les pictogrammes sont
définis en SVG ; les exports PNG et ICO se régénèrent avec `tools/build_icons.py`.
Le rendu Windows utilise FreeType et un lissage en niveaux de gris pour éviter
les franges colorées sur les petits textes du thème sombre.

## Fichiers et sécurité

Les clés restent dans `%USERPROFILE%\.ssh`. Les passphrases sont traitées en
mémoire par `cryptography`, sans argument de processus ni fichier de passphrase.
Les nouvelles clés privées et les exports privés ont des permissions limitées au
propriétaire, à SYSTEM et aux administrateurs Windows.

La configuration est écrite atomiquement avec une sauvegarde `config.harpie.bak`.
Un renommage met à jour les références exactes à la clé et conserve les alias Host.
Une suppression retire seulement les directives `IdentityFile` correspondantes ;
les autres options et les alias restent disponibles.

Les clés supprimées sont conservées dans `.ssh/.harpie-trash`, avec des permissions
restreintes. Cette corbeille n'est pas une sauvegarde externe : elle disparaît si
le disque est perdu. Les clés peuvent y être restaurées avec leur tag et leurs
références SSH, sans écraser les modifications de config plus récentes.

Les tags sont dans `%APPDATA%\HarpieSSH\metadata.json`. Les métadonnées corrompues
sont sauvegardées avant récupération. Les logs tournants sont dans
`%LOCALAPPDATA%\HarpieSSH\logs`, y compris pour l'exécutable.

La gestion des clés est locale. Se connecter à un serveur ou ouvrir GitHub crée
une connexion réseau uniquement après action explicite dans l'interface.
La clé publique doit être installée séparément sur le serveur ou sur GitHub.
La clé privée n'est jamais affichée ; son export demande confirmation.

Le commentaire éditable est celui du fichier `.pub`, sans modifier le secret privé.
Les clés OpenSSH chiffrées sont inspectées via leur partie publique ; leur secret
ne peut être intégralement vérifié sans la passphrase. L'import et la réparation
effectuent cette vérification après saisie.
Les fichiers PuTTY `.ppk` doivent d'abord être convertis en OpenSSH avec PuTTYgen.
Pour SSH Agent, activer le service Windows **OpenSSH Authentication Agent**.
La passphrase est saisie directement dans le terminal lors d'un ajout à l'agent.

## Vérification et build

```powershell
.venv\Scripts\python.exe -B -m unittest discover -s tests -v
.venv\Scripts\python.exe tools\build_icons.py
.venv\Scripts\python.exe -m PyInstaller --noconfirm harpie.spec
```

Les tests créent leurs propres fichiers dans des dossiers temporaires du projet.
Ils ne lisent et ne modifient jamais les vraies clés.

Pour un diagnostic de l'exécutable, `HARPIE_HOME` permet d'isoler **toutes** ses
données dans un dossier de test. `--self-check` exige cette variable et vérifie le
démarrage, le support des clés chiffrées, les assets et la police sans ouvrir de fenêtre.
Il écrit `self-check.json` dans ce dossier. Ne pas définir `HARPIE_HOME` pour
l'usage quotidien.
