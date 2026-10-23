import html
import re
import unicodedata
from datetime import UTC, datetime

from dateutil import parser


def clean_text(text: str) -> str:
    """Nettoie le texte en supprimant les balises HTML et en normalisant les espaces."""
    if not text:
        return ""

    # Désérialise les entités HTML
    text = html.unescape(text)

    # Supprime les balises HTML
    text = re.sub(r"<[^>]+>", "", text)

    # Normalise les espaces
    text = re.sub(r"\s+", " ", text).strip()

    return text


def parse_date(date_str: str) -> datetime:
    """Parse une date string en objet datetime."""
    if not date_str:
        return None

    try:
        # Essaye de parser avec dateutil (gère plusieurs formats)
        dt = parser.parse(date_str)

        # Assure que la timezone est définie (UTC par défaut)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=UTC)

        return dt
    except (ValueError, TypeError):
        return None


def fix_encoding(text: str) -> str:
    """Répare les problèmes d'encodage courants (ex: Ã© -> é)."""
    if not text:
        return ""
    try:
        # Tente de ré-encoder/décoder si le texte contient du mojibake
        return text.encode("latin1").decode("utf-8")
    except (UnicodeEncodeError, UnicodeDecodeError):
        return text


def truncate_text(text: str, max_len: int = 300) -> str:
    """Borne la longueur de l'extrait sans couper les mots au milieu."""
    if not text or len(text) <= max_len:
        return text
    truncated = text[:max_len].rsplit(" ", 1)[0]
    return f"{truncated}..."


def slugify_category(text: str) -> str:
    if not text:
        return "non-classe"

    # 1. Décompose les caractères accentués (ex: 'é' -> 'e' + accent)
    text = unicodedata.normalize("NFD", text)
    # 2. Supprime les accents
    text = "".join(c for c in text if unicodedata.category(c) != "Mn")
    # 3. Mettre en minuscules
    text = text.lower()
    # 4. Remplacer tout ce qui n'est pas lettre/chiffre par un tiret
    text = re.sub(r"[^a-z0-9]+", "-", text)
    # 5. Nettoyer les tirets aux extrémités
    return text.strip("-")


STOPWORDS_FR = {
    "le",
    "la",
    "les",
    "un",
    "une",
    "des",
    "du",
    "de",
    "d",
    "l",
    "et",
    "en",
    "a",
    "pour",
    "sur",
    "par",
    "dans",
    "est",
    "au",
    "aux",
    "qui",
    "que",
    "avec",
    "ce",
    "ces",
    "cette",
    "son",
    "sa",
    "ses",
    "sans",
    "sous",
    "vers",
    "chez",
    "mais",
    "ou",
    "donc",
    "or",
    "ni",
    "car",
    "plus",
    "moins",
    "tres",
    "tout",
    "tous",
    "toute",
    "toutes",
    "apres",
    "avant",
    "entre",
    "comme",
    "leur",
    "leurs",
    "sont",
    "ete",
}


def _normaliser_mot(mot: str) -> str:
    """Passe en minuscules et retire les accents."""
    mot_sans_accent = unicodedata.normalize("NFD", mot.lower())
    return "".join(c for c in mot_sans_accent if unicodedata.category(c) != "Mn")


def tokenize_title(title: str) -> set[str]:
    """Nettoie et découpe un titre en un ensemble de mots significatifs normalisés."""
    if not title:
        return set()
    # Normalise les apostrophes courantes
    texte = title.replace("’", "'")
    words = re.findall(r"\b\w+\b", texte)
    tokens = set()
    for w in words:
        clean_w = _normaliser_mot(w)
        if clean_w not in STOPWORDS_FR and len(clean_w) > 2:
            tokens.add(clean_w)
    return tokens


def jaccard_similarity(title_a: str, title_b: str) -> float:
    """Calcule l'indice de Jaccard entre deux titres (valeur entre 0.0 et 1.0)."""
    if not title_a or not title_b:
        return 0.0

    # Normalisation basique
    norm_a = _normaliser_mot(title_a).strip()
    norm_b = _normaliser_mot(title_b).strip()
    if norm_a == norm_b:
        return 1.0

    set_a = tokenize_title(title_a)
    set_b = tokenize_title(title_b)

    if not set_a or not set_b:
        return 1.0 if set_a == set_b and (norm_a and norm_b) else 0.0

    intersection = len(set_a & set_b)
    union = len(set_a | set_b)

    return intersection / union if union else 0.0


def is_duplicate_jaccard(title_a: str, title_b: str, threshold: float = 0.65) -> bool:
    """Détermine si deux titres sont des doublons selon le seuil défini."""
    return jaccard_similarity(title_a, title_b) >= threshold
