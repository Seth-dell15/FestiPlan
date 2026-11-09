import html
import re


class InputSanitizer:
    """Composant de nettoyage et de neutralisation des entrées textuelles contre les attaques XSS."""

    # Détection des motifs d'injection de script ou d'événements JavaScript (XSS)
    _XSS_PATTERNS = [
        re.compile(r"<\s*script[^>]*>.*?<\s*/\s*script\s*>", re.IGNORECASE | re.DOTALL),
        re.compile(r"<\s*iframe[^>]*>.*?<\s*/\s*iframe\s*>", re.IGNORECASE | re.DOTALL),
        re.compile(r"javascript\s*:", re.IGNORECASE),
        re.compile(r"on\w+\s*=", re.IGNORECASE),  # onload=, onerror=, onclick=
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

        # Échapper les caractères HTML réservés (<, >, &, ", ')
        return html.escape(cleaned)

    @classmethod
    def contains_xss_threat(cls, text: str) -> bool:
        """Vérifie si une chaîne contient une tentative manifeste d'injection de script."""
        if not text:
            return False
        for pattern in cls._XSS_PATTERNS:
            if pattern.search(text):
                return True
        return "<script" in text.lower() or "onerror=" in text.lower() or "javascript:" in text.lower()
