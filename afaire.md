# Harpie — périmètre personnel

Ce logiciel est uniquement pour moi. L'objectif est de gérer mes clés SSH sans
retaper des commandes ni éditer les fichiers manuellement.

## Réalisé

- Création Ed25519 / RSA 4096 ; passphrases traitées en mémoire.
- Import OpenSSH / PEM et export local public / privé.
- Tags, recherche, tri et commentaires complets.
- Configuration des serveurs et ports ; connexion et SSH Agent.
- Écritures atomiques, sauvegarde du config, collisions de noms vérifiées.
- Retour arrière en cas d'échec du renommage ou de la suppression.
- Corbeille privée et restauration.
- Détection des paires incohérentes, des fichiers manquants et des permissions.
- Réparation de la clé publique et protection du fichier privé.
- Vérification des clés et modification des passphrases dans l'interface.
- Tâches en arrière-plan, détails défilants et raccourcis clavier.
- Tests isolés et build Windows.

## Évolutions possibles si j'en ai besoin

- Conversion automatique PuTTY `.ppk` si PuTTYgen est installé.
- Thème sombre.
- Installation de la clé publique sur un VPS, avec une connexion explicitement demandée.
- Sauvegarde personnelle chiffrée sur un support séparé.

Aucune fonction de publication, compte, cloud, télémétrie ou multi-utilisateur.
