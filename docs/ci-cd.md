# Stratégie CI/CD

1. Outil : GitHub Actions, gratuit pour un dépôt public et intégré à la forge ; GitLab CI demanderait de migrer le dépôt, Jenkins un serveur à maintenir.
2. Déclencheurs : chaque push sur `main` et chaque pull request (`.github/workflows/ci.yml`).
3. Étapes : `lint` (ruff check et ruff format --check) et `tests` (pytest) en parallèle, puis `image` seulement si les deux sont verts.
4. Les tests n'appellent jamais le réseau : flux enregistrés dans `tests/fixtures/`, transport HTTP simulé.
5. Image : Dockerfile multi-étapes, image finale `python:3.12-slim` sans outils de développement, utilisateur non root (uid 10001).
6. Publication : sur `main` uniquement, dans `ghcr.io/cocoalice03/la_gazette_news`, avec le tag `AAAAMMJJHHMMSS-sha` (horodatage UTC et 7 premiers caractères du commit) et `latest`. Sur une pull request, l'image est construite mais pas publiée.
7. Traçabilité : l'image porte les labels OCI `org.opencontainers.image.revision` (commit) et `org.opencontainers.image.source` (dépôt).
8. Garde-fou : la protection de la branche `main` exige les contrôles `lint`, `tests` et `image` verts et une relecture avant fusion ; une CI rouge bloque donc le merge.
9. Vérification : une branche `test/ci-rouge` qui casse volontairement un test doit afficher une CI rouge et un bouton de fusion bloqué.
10. Hors périmètre au TD 2 : déploiement automatique (TD 7), matrice de versions, cache exotique ; seul le cache de couches Docker de GitHub Actions est utilisé.
