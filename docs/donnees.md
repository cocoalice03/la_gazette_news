# Dictionnaire de données

Début du dictionnaire, posé au TD 3 avec la collecte. Il s'enrichira au TD 4 (`articles_propres`) puis avec les thèmes.

## Périmètre

On ne garde que le titre, un extrait, le lien, les dates et la rubrique d'un article. Jamais le texte intégral, les images, les commentaires ni l'auteur (donnée personnelle). Ce bornage est appliqué dès la collecte, y compris dans le `payload`.

## `articles_bruts/` : les items tels que reçus

Un fichier JSON par item : `data/articles_bruts/<source>/<id>.json`, où `<source>` est le nom de la source en minuscules sans accents (`le-monde`, `ouest-france`). Le dossier passera dans un bucket MinIO du même nom quand l'infrastructure de production arrivera.

| Champ | Type | Description |
|---|---|---|
| `id` | texte (32 car. hexadécimaux) | 32 premiers caractères du SHA-256 de `source` + `lien`. Clé naturelle de l'item : il ne s'écrit qu'une fois |
| `source` | texte | Nom de la source, tel que dans `sources.csv` |
| `lien` | texte (URL) | Lien de l'article. Un item sans lien est ignoré |
| `titre` | texte ou null | Titre, entités HTML décodées et espaces réduits. Null si absent du flux |
| `resume` | texte ou null | Description ou résumé du flux, sans balises HTML, tronqué à 300 caractères sur une fin de mot |
| `publie_le` | date ISO 8601 UTC ou null | `pubDate` (RSS) ou `published`, à défaut `updated` (Atom). Null si absente |
| `recupere_le` | date ISO 8601 UTC | Début du passage de collecte qui a écrit l'item |
| `rubrique` | texte ou null | Première catégorie du flux, à défaut premier segment du chemin du lien (`/environnement/climat/...` donne `environnement`) |
| `payload` | objet JSON | Entrée du flux telle que lue par feedparser, moins les champs exclus ci-dessous et les dates déjà converties (`*_parsed`) |

Champs retirés du `payload` : `author`, `author_detail`, `authors`, `contributors`, `publisher`, `publisher_detail` (personnes), `content` (texte intégral), `media_content`, `media_thumbnail`, `media_credit`, `credit`, `enclosures`, `image` et les liens `rel="enclosure"` (images), `comments`, `wfw_commentrss`, `slash_comments` (commentaires).

Un item sans titre ou sans date est gardé : c'est au nettoyage (TD 4) de décider s'il entre dans `articles_propres`.

## Table `sources`

Migration `src/gazette/migrations/001_sources.sql`. Une ligne par source de `sources.csv`, synchronisée au début de chaque passage. La synchronisation met à jour `type` et `url_flux` sans toucher à l'état de collecte.

| Colonne | Type | Description |
|---|---|---|
| `nom` | text, clé primaire | Nom de la source |
| `type` | text | `PQR` ou `PQN` |
| `url_flux` | text | URL du flux RSS ou Atom (colonne `acces` de `sources.csv`) |
| `actif` | boolean | Faux quand la source est en sommeil : elle n'est plus interrogée |
| `derniere_reussite` | timestamptz | Dernier passage réussi (200 ou 304) |
| `echecs_consecutifs` | integer | Remis à 0 à chaque réussite. À 3, la source passe en sommeil |
| `etag` | text | ETag de la dernière réponse 200, renvoyé en `If-None-Match` |
| `last_modified` | text | Last-Modified de la dernière réponse 200, renvoyé en `If-Modified-Since` |
| `derniere_erreur` | text | Message du dernier échec (`HTTP 403`, `ConnectError : ...`, `flux illisible : ...`) |
| `en_sommeil_depuis` | timestamptz | Date de mise en sommeil, null si active |

ETag et Last-Modified sont oubliés si l'URL du flux change dans `sources.csv`.

## Table `passages`

Migration `002_passages.sql`. Une ligne par source et par passage : c'est l'historique qui répond à « combien d'articles par source, et lesquelles ont dormi ? ».

| Colonne | Type | Description |
|---|---|---|
| `id` | bigserial | Identifiant |
| `source` | text | Référence `sources.nom` |
| `debut` | timestamptz | Début de la lecture de la source |
| `duree_ms` | integer | Durée, essais compris |
| `statut` | text | `ok` (200), `non_modifie` (304) ou `echec` |
| `code_http` | integer | Dernier code HTTP reçu, null si aucune réponse |
| `recus` | integer | Entrées présentes dans le flux |
| `ecrits` | integer | Items nouveaux écrits dans `articles_bruts/` |
| `ignores` | integer | Entrées non écrites : déjà présentes ou sans lien |
| `erreur` | text | Motif de l'échec |

## Table `schema_migrations`

Versions appliquées (`001_sources`, `002_passages`...) et leur date. Une migration ne s'applique qu'une fois ; un verrou consultatif PostgreSQL empêche deux applications simultanées.

## Requêtes utiles

```sql
-- articles écrits par source depuis le début
SELECT source, sum(ecrits) AS articles FROM passages GROUP BY source ORDER BY articles DESC;

-- sources en sommeil ou en difficulté
SELECT nom, actif, echecs_consecutifs, derniere_erreur, en_sommeil_depuis
FROM sources WHERE NOT actif OR echecs_consecutifs > 0;
```
# Contrat de données & Conformité

## 1. Schéma cible (`articles_propres`)
Seules les données autorisées à la réutilisation sont conservées :
- `id` (hash unique)
- `raw_id` (traçabilité vers l'item brut)
- `source_id` (nom du média)
- `title` (titre normalisé)
- `summary` (extrait court, max 300 char)
- `url` (lien d'origine)
- `published_at` (date UTC)

> **Conformité RGPD** : Aucune donnée personnelle, nom d'auteur ou commentaire d'utilisateur n'est stocké.

## 2. Politique de rétention
- **Données brutes (`articles_bruts`)** : Rétention de 90 jours, puis purge automatique.
- **Éditions / Gazette (`articles_propres`)** : Conservation de 30 jours en base active, puis archivage en stockage froid (JSON/Parquet compressé).

## 3. Normalisation des rubriques (Mapping)
Pour corriger la disparité observée entre sources (*Vox Politique*, *societe*, *etudiant*), un mapping unifié est appliqué :
- `societe`, `société`, `faits-divers` ➔ `societe`
- `vox-politique`, `politique` ➔ `politique`
- `tech-web`, `high-tech`, `pixels` ➔ `technologie`