# Qualité des données

## Items qui n'ont rien à faire dans une gazette

Premier relevé fait le 22 octobre 2026 sur les 106 items des premiers passages (Le Figaro, Le Monde, Libération, Sud Ouest). À compléter après une semaine de collecte, avant le TD 4. Chaque cas donne une règle candidate pour le nettoyage.

| # | Source | Rubrique | Titre (début) | Pourquoi l'écarter | Règle candidate |
|---|---|---|---|---|---|
| 1 | Le Figaro | Bons plans High-Tech | Roi du milieu de gamme, ce smartphone Xiaomi fait l'unanimité en promo | Contenu commercial (affiliation) | Rubrique contenant « Bons plans » ; lien sous `/bons-plans/` |
| 2 | Le Figaro | Bons plans | Bons plans DAZN : ces deux offres folles pour suivre le meilleur du football | Contenu commercial | Idem |
| 3 | Le Figaro | Guides | Corée du Sud et nulle part ailleurs : les expériences touristiques les plus folles | Guide de consommation, pas une actualité | Rubrique « Guides » |
| 4 | Le Monde | societe | EN DIRECT, manifestations du 17 octobre : un conseil de sécurité en cours | Page de direct : son titre change toute la journée, ce n'est pas un article | Titre commençant par « EN DIRECT » ou « DIRECT. » ; lien contenant `/live/` |
| 5 | Libération | societe | EN DIRECT – Mouvement social : interdiction de « toute manifestation » à Lyon | Page de direct | Idem |
| 6 | Sud Ouest | politique | DIRECT. Mobilisation sociale et violences : 20 % de forces de l'ordre en plus | Page de direct | Idem |
| 7 | Libération | societe | Mobilisation sociale : des manifestations interdites à Paris, Lyon, Rouen | Direct dont le titre a changé : le lien contient encore `en-direct-violences-du-17-octobre` | Lien contenant `en-direct` |
| 8 | Libération | international | EN IMAGES - La jeunesse d'Europe se révolte | Galerie de photos : rien à résumer sans les images, qu'on ne garde pas | Titre commençant par « EN IMAGES » |
| 9 | Libération | international | Tempête Austen, interdictions de manifester… L'actu de ce jeudi 22 octobre au matin | Récapitulatif quotidien qui reprend d'autres articles, résumé de 67 caractères | Titre contenant « L'actu de ce » ; résumé de moins de 80 caractères |
| 10 | Sud Ouest | gironde | Les Prix Médias et Ruralités récompensent Valérie Deymes, journaliste à « Sud Ouest » | Autopromotion du journal | À trancher en équipe : règle sur le nom de la source dans le titre, ou liste manuelle |

## Autres constats pour le TD 4

- **Même information, plusieurs sources.** « 43 % des Français à découvert » (Libération, Sud Ouest), le virus Shamonda (Libération, Sud Ouest), la tempête Austen (Le Monde, Libération, Sud Ouest). Ce ne sont pas des doublons à supprimer : c'est la matière des thèmes. Le regroupement se fera là.
- **Rubriques hétérogènes.** Le Figaro donne des catégories (« Vox Politique », « Tech & Web »), les autres une rubrique déduite du lien (`societe`, `haute-vienne`, `etudiant`). Il faudra une table de correspondance vers une liste commune.
- **Champs manquants.** Aucun item sans titre ni sans date dans ce premier relevé. Le cas est gardé dans `articles_bruts` et devra être traité par le nettoyage.
- **Sources muettes.** Ouest-France (robots.txt), Les Échos (403), Le Télégramme (connexion refusée) et La Voix du Nord (flux vide) ne donnent rien. Voir `docs/exploitation.md`.
