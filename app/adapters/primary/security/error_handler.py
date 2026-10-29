import logging
from fastapi import Request, HTTPException
from fastapi.exception_handlers import http_exception_handler
from starlette.responses import JSONResponse, Response
from starlette.status import HTTP_500_INTERNAL_SERVER_ERROR

logger = logging.getLogger("festiplan.security")


async def global_security_exception_handler(request: Request, exc: Exception) -> Response:
    """Gestionnaire global d'exceptions pour prévenir la fuite d'informations système (OWASP Information Disclosure).
    
    Les HTTPException prévues (400, 404, 422...) sont transmises normalement avec leurs messages métier.
    En revanche, toute exception système ou BDD inattendue est consignée en interne dans les logs du serveur
    avec sa stack trace complète, et le client reçoit une réponse 500 anonymisée et sécurisée.
    """
    if isinstance(exc, HTTPException):
        return await http_exception_handler(request, exc)

    logger.error(
        "Exception non gérée interceptée sur %s %s : %s",
        request.method,
        request.url.path,
        str(exc),
        exc_info=True,
    )

    return JSONResponse(
        status_code=HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "detail": "Une erreur interne sécurisée est survenue. Aucun détail technique sensible n'est divulgué.",
            "status": "error",
        },
    )

