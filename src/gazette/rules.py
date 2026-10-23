from collections.abc import Iterable

from gazette.normalization import is_duplicate_jaccard


def check_exclusion_rules(
    article: dict,
    existing_titles: Iterable[str] | None = None,
    duplicate_threshold: float = 0.65,
) -> tuple[bool, str | None]:
    """Vérifie si un article doit être exclu.

    Retourne (True, None) si l'article est conservé,
    ou (False, "RXX_nom") s'il est rejeté.
    """
    title = article.get("title", "").strip()
    summary = article.get("summary", "").strip()
    category = article.get("category_slug", "")
    url = article.get("url", "").lower()
    source = article.get("source_id", "").lower()

    # R06 : Champs manquants
    if not title or not article.get("published_at"):
        return False, "R06_empty"

    # R01 : Contenu commercial / Bons plans / Guides
    if "bons-plans" in category or "guides" in category or "/bons-plans/" in url:
        return False, "R01_publi"

    # R02 : Pages de direct / Live
    title_upper = title.upper()
    if (
        title_upper.startswith("EN DIRECT")
        or title_upper.startswith("DIRECT.")
        or "/live/" in url
        or "en-direct" in url
    ):
        return False, "R02_direct"

    # R03 : Galeries photos / Vidéos
    if title_upper.startswith("EN IMAGES") or title_upper.startswith("EN PHOTOS"):
        return False, "R03_galerie"

    # R04 : Récapitulatifs / Résumés trop courts
    if "l'actu de ce" in title.lower() or len(summary) < 80:
        return False, "R04_recap"

    # R05 : Autopromotion (ex: "à « Sud Ouest »")
    # Normalise la source (tirets → espaces) pour la comparaison
    source_normalized = source.replace("-", " ")
    titre_bas = title.lower()
    if f"« {source_normalized} »" in titre_bas or f"journal {source_normalized}" in titre_bas:
        return False, "R05_autopromo"

    # R07 : Doublon approximatif (titres proches entre sources ou dans le même lot)
    if existing_titles:
        for existing_title in existing_titles:
            if is_duplicate_jaccard(title, existing_title, threshold=duplicate_threshold):
                return False, "R07_doublon"

    return True, None


def filter_articles_and_duplicates(
    articles: list[dict],
    duplicate_threshold: float = 0.65,
) -> tuple[list[dict], list[tuple[dict, str]]]:
    """Applique les règles de filtrage unitaire et de dédoublonnage approximatif sur un lot.

    Retourne :
        - valides : liste des articles conservés (conformes et uniques)
        - rejetes : liste de tuples (article, raison_du_rejet)
    """
    valides: list[dict] = []
    rejetes: list[tuple[dict, str]] = []
    titres_acceptes: list[str] = []

    for article in articles:
        est_valide, raison = check_exclusion_rules(
            article,
            existing_titles=titres_acceptes,
            duplicate_threshold=duplicate_threshold,
        )
        if est_valide:
            valides.append(article)
            titres_acceptes.append(article.get("title", ""))
        else:
            rejetes.append((article, raison or "R99_inconnu"))

    return valides, rejetes
