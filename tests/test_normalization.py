from gazette.normalization import (
    clean_text,
    fix_encoding,
    is_duplicate_jaccard,
    jaccard_similarity,
    parse_date,
    slugify_category,
    tokenize_title,
    truncate_text,
)


# 1. Test du nettoyage HTML
def test_clean_text():
    raw = "<p>Un titre avec <b>du gras</b> &amp; des entités</p>"
    assert clean_text(raw) == "Un titre avec du gras & des entités"


def test_clean_text_chaine_vide():
    assert clean_text("") == ""


# 2. Test de la correction d'encodage (mojibake)
def test_fix_encoding():
    raw = "Un texte cassÃ©"
    assert fix_encoding(raw) == "Un texte cassé"


# 3. Test de la normalisation des espaces (inclut dans clean_text)
def test_clean_spaces():
    raw = "  Un   titre \n avec   trop   d'espaces.  "
    assert clean_text(raw) == "Un titre avec trop d'espaces."


# 4. Test du slugify des rubriques (Étape essentielle de ton relevé)
def test_slugify_category():
    # Cas avec majuscules et accents
    assert slugify_category("Économie et Finance") == "economie-et-finance"
    # Cas avec espaces et symboles
    assert slugify_category(" Bons plans High-Tech ") == "bons-plans-high-tech"
    # Cas chaîne vide
    assert slugify_category("") == "non-classe"


# 5. Test de la conversion des dates en UTC
def test_parse_date():
    raw = "Thu, 22 Oct 2026 14:30:00 +0200"
    result = parse_date(raw)
    assert result is not None
    assert result.tzinfo is not None


# 6. Test de la limitation de longueur de l'extrait
def test_truncate_text():
    raw = "Ceci est un extrait de texte assez long qui doit être coupé sans hacher le mot."
    # À 35 caractères max, le mot "assez" (34 caractères) est inclus
    assert truncate_text(raw, max_len=35) == "Ceci est un extrait de texte assez..."


# 7. Test de la tokenisation pour dédoublonnage Jaccard
def test_tokenize_title():
    titre = "Tempête Austen : trois départements placés en vigilance rouge !"
    tokens = tokenize_title(titre)
    # Les accents sont retirés, les stopwords et mots courts (< 3 car) sont éliminés
    assert "tempete" in tokens
    assert "austen" in tokens
    assert "trois" in tokens
    assert "departements" in tokens
    assert "places" in tokens
    assert "vigilance" in tokens
    assert "rouge" in tokens
    assert "en" not in tokens  # stopword


# 8. Test de la similarité de Jaccard
def test_jaccard_similarity_quasi_identiques():
    t1 = "Tempête Austen : trois départements en vigilance rouge"
    t2 = "Tempête Austen : trois départements placés en vigilance rouge"
    # Les titres sont très proches
    sim = jaccard_similarity(t1, t2)
    assert sim >= 0.7
    assert is_duplicate_jaccard(t1, t2, threshold=0.7) is True


def test_jaccard_similarity_differents():
    t1 = "Tempête Austen : trois départements en vigilance rouge"
    t2 = "Le gouvernement annonce une réforme des retraites"
    sim = jaccard_similarity(t1, t2)
    assert sim < 0.2
    assert is_duplicate_jaccard(t1, t2, threshold=0.7) is False
