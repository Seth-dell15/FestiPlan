from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import Response


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Middleware HTTP injectant les en-têtes de sécurité recommandés par l'OWASP."""

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        response = await call_next(request)

        # 1. Empêcher le MIME-type sniffing (attaque par interprétation de fichiers malveillants)
        response.headers["X-Content-Type-Options"] = "nosniff"

        # 2. Protection contre le Clickjacking (interdire l'intégration dans des iframes externes)
        response.headers["X-Frame-Options"] = "DENY"

        # 3. Protection XSS pour navigateurs historiques
        response.headers["X-XSS-Protection"] = "1; mode=block"

        # 4. Politique de référencement stricte pour ne pas faire fuiter d'URLs sensibles
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"

        # 5. Restriction des permissions du navigateur (caméra, micro, géolocalisation)
        response.headers["Permissions-Policy"] = "geolocation=(), microphone=(), camera=()"

        # 6. Content-Security-Policy (CSP) : autorise les scripts Swagger tout en bloquant les injections non autorisées
        response.headers["Content-Security-Policy"] = (
            "default-src 'self'; "
            "script-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net; "
            "style-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net; "
            "img-src 'self' data: https://fastapi.tiangolo.com; "
            "frame-ancestors 'none';"
        )

        return response
