# Contribuer

## Branches

- `main` est toujours déployable. Personne ne pousse directement dessus.
- Une branche par sujet, créée depuis `main` : `feat/<sujet>`, `fix/<sujet>`, `docs/<sujet>`, `ci/<sujet>`. Exemple : `feat/collecte-etag`.
- Une branche vit peu de temps : on la fusionne dans la journée ou on la découpe.

## Commits

Format Conventional Commits, en français, à l'impératif :

```
<type>(<portée facultative>): <description courte>
```

Types : `feat`, `fix`, `docs`, `test`, `ci`, `refactor`, `chore`. Exemple : `feat(collecte): ajouter la requête conditionnelle ETag`.

## Pull requests

1. Pousser la branche et ouvrir une pull request vers `main`.
2. La CI doit être verte : lint, tests, construction de l'image. Une CI rouge bloque la fusion.
3. Une relecture d'un autre membre de l'équipe est obligatoire, même rapide.
4. L'auteur fusionne après approbation, en « Squash and merge ».

## Avant de pousser

```sh
bin/test
```

## Règles du projet

- Jamais de texte intégral, d'image, de commentaire ni de donnée personnelle (l'auteur d'un article n'est pas stocké).
- Toute nouvelle source passe par `sources.csv` avec ses conditions d'utilisation vérifiées à la main.
- Aucun secret dans le dépôt : les valeurs vont dans `.env` (ignoré par Git), seul `.env.example` est commité.
- Rien n'est installé ni configuré à la main sans être décrit dans le dépôt.
