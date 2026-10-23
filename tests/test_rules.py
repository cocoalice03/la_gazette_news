from gazette.rules import check_exclusion_rules, filter_articles_and_duplicates


def test_rule_r01_bons_plans():
    article = {
        "title": "Smartphone Xiaomi en promo",
        "category_slug": "bons-plans-high-tech",
        "url": "https://lefigaro.fr/bons-plans/123",
        "published_at": "2026-10-22T10:00:00Z",
    }
    is_valid, rule = check_exclusion_rules(article)
    assert is_valid is False
    assert rule == "R01_publi"


def test_rule_r02_en_direct():
    article = {
        "title": "EN DIRECT, manifestations du 17 octobre",
        "category_slug": "societe",
        "url": "https://lemonde.fr/societe/article",
        "published_at": "2026-10-22T10:00:00Z",
    }
    is_valid, rule = check_exclusion_rules(article)
    assert is_valid is False
    assert rule == "R02_direct"


def test_rule_r03_galerie():
    article = {
        "title": "EN IMAGES - La jeunesse se révolte",
        "category_slug": "international",
        "url": "https://liberation.fr/international",
        "published_at": "2026-10-22T10:00:00Z",
    }
    is_valid, rule = check_exclusion_rules(article)
    assert is_valid is False
    assert rule == "R03_galerie"


def test_rule_r04_recap():
    article = {
        "title": "L'actu de ce jeudi 22 octobre",
        "summary": "Court",
        "category_slug": "societe",
        "url": "https://liberation.fr/societe",
        "published_at": "2026-10-22T10:00:00Z",
    }
    is_valid, rule = check_exclusion_rules(article)
    assert is_valid is False
    assert rule == "R04_recap"


def test_rule_r05_autopromo():
    resume_long = (
        "Ceci est un extrait de résumé suffisamment détaillé et long "
        "pour passer la règle R04 qui exige au moins 80 caractères."
    )
    article = {
        "title": "Les Prix Médias récompensent Valérie, journaliste à « Sud Ouest »",
        "summary": resume_long,
        "source_id": "sud-ouest",  # avec tiret, sera normalisé en "sud ouest"
        "category_slug": "gironde",
        "url": "https://sudouest.fr/gironde",
        "published_at": "2026-10-22T10:00:00Z",
    }
    is_valid, rule = check_exclusion_rules(article)
    assert is_valid is False
    assert rule == "R05_autopromo"


def test_rule_r06_champs_manquants():
    article = {
        "title": "",  # Titre vide
        "category_slug": "societe",
        "url": "https://lemonde.fr/societe",
        "published_at": "2026-10-22T10:00:00Z",
    }
    is_valid, rule = check_exclusion_rules(article)
    assert is_valid is False
    assert rule == "R06_empty"


def test_article_accepte():
    """Cas positif : un article valide qui passe toutes les règles."""
    resume_long = (
        "Ceci est un extrait de résumé suffisamment détaillé et long "
        "pour passer la règle R04 qui exige au moins 80 caractères."
    )
    article = {
        "title": "Une actualité importante",
        "summary": resume_long,
        "category_slug": "politique",
        "url": "https://lemonde.fr/politique/article",
        "source_id": "le-monde",
        "published_at": "2026-10-22T10:00:00Z",
    }
    is_valid, rule = check_exclusion_rules(article)
    assert is_valid is True
    assert rule is None


def test_rule_r07_doublon_approximatif():
    titres_existants = ["Tempête Austen : trois départements en vigilance rouge"]
    resume_long = (
        "Ceci est un extrait de résumé suffisamment détaillé et long "
        "pour passer la règle R04 qui exige au moins 80 caractères."
    )
    article = {
        "title": "Tempête Austen : trois départements placés en vigilance rouge",
        "summary": resume_long,
        "category_slug": "meteo",
        "url": "https://liberation.fr/environnement/article",
        "source_id": "liberation",
        "published_at": "2026-10-22T10:00:00Z",
    }
    is_valid, rule = check_exclusion_rules(article, existing_titles=titres_existants)
    assert is_valid is False
    assert rule == "R07_doublon"


def test_filter_articles_and_duplicates():
    resume = (
        "Ceci est un extrait de résumé suffisamment détaillé et long "
        "pour passer la règle R04 qui exige au moins 80 caractères."
    )
    articles = [
        {
            "title": "Tempête Austen : trois départements en vigilance rouge",
            "summary": resume,
            "category_slug": "meteo",
            "url": "https://lemonde.fr/article-1",
            "source_id": "le-monde",
            "published_at": "2026-10-22T10:00:00Z",
        },
        {
            "title": "Tempête Austen : trois départements placés en vigilance rouge",
            "summary": resume,
            "category_slug": "meteo",
            "url": "https://liberation.fr/article-2",
            "source_id": "liberation",
            "published_at": "2026-10-22T10:00:00Z",
        },
        {
            "title": "Une réforme économique annoncée par le gouvernement",
            "summary": resume,
            "category_slug": "economie",
            "url": "https://lefigaro.fr/article-3",
            "source_id": "le-figaro",
            "published_at": "2026-10-22T10:00:00Z",
        },
    ]

    valides, rejetes = filter_articles_and_duplicates(articles)
    assert len(valides) == 2
    assert len(rejetes) == 1
    assert rejetes[0][1] == "R07_doublon"
    assert valides[0]["title"] == "Tempête Austen : trois départements en vigilance rouge"
    assert valides[1]["title"] == "Une réforme économique annoncée par le gouvernement"
