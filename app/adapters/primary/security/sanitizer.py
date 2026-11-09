import re


class InputSanitizer:
    """Composant de nettoyage et de neutralisation des entrées textuelles contre les attaques XSS."""

    # Détection des motifs d'injection de script ou d'événements JavaScript (XSS)
    _XSS_PATTERNS = [
        re.compile(r"<\s*script[^>]*>.*?<\s*/\s*script\s*>", re.IGNORECASE | re.DOTALL),
        re.compile(r"<\s*iframe[^>]*>.*?<\s*/\s*iframe\s*>", re.IGNORECASE | re.DOTALL),
        re.compile(r"javascript\s*:", re.IGNORECASE),
        re.compile(r"\bon\w+\s*=", re.IGNORECASE),  # onload=, onerror=, onclick=
    ]

    @classmethod
    def sanitize_text(cls, text: str) -> str:
        """Nettoie une chaîne de caractères en supprimant les scripts dangereux et en échappant les balises HTML."""
        if not text:
            return ""

        cleaned = text.strip()
        # Supprimer les balises <script>...</script> explicites
        for pattern in cls._XSS_PATTERNS:
            cleaned = pattern.sub("", cleaned)

        # Seuls les chevrons ouvrent une balise : &, ' et " restent intacts pour ne pas altérer les noms.
        return cleaned.replace("<", "&lt;").replace(">", "&gt;")
