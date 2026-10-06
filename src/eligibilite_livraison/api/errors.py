"""Traduction des exceptions en réponses ``Error`` du contrat."""

import logging

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from eligibilite_livraison.api.schemas import ErrorResponse
from eligibilite_livraison.domain import errors

logger = logging.getLogger(__name__)

_STATUS_BY_ERROR: dict[type[errors.DomainError], int] = {
    errors.OrderNotFoundError: 404,
    errors.DuplicateOrderError: 422,
    errors.ModelUnavailableError: 503,
}


def _error_response(status_code: int, error: str, message: str, details=None) -> JSONResponse:
    body = ErrorResponse(error=error, message=message, details=details)
    return JSONResponse(status_code=status_code, content=body.model_dump(exclude_none=True))


def _status_for(error: errors.DomainError) -> int:
    for error_class in type(error).__mro__:
        if error_class in _STATUS_BY_ERROR:
            return _STATUS_BY_ERROR[error_class]
    return 500


def register_error_handlers(app: FastAPI) -> None:
    @app.exception_handler(RequestValidationError)
    async def handle_validation_error(_: Request, exc: RequestValidationError) -> JSONResponse:
        details = [
            f"{'.'.join(str(part) for part in item['loc'][1:])}: {item['msg']}"
            for item in exc.errors()
        ]
        return _error_response(422, "validation_error", "Requête invalide.", details)

    @app.exception_handler(errors.DomainError)
    async def handle_domain_error(_: Request, exc: errors.DomainError) -> JSONResponse:
        status_code = _status_for(exc)
        if status_code >= 500:
            logger.error("Erreur métier %s : %s", exc.code, exc)
        return _error_response(status_code, exc.code, str(exc))

    @app.exception_handler(StarletteHTTPException)
    async def handle_http_error(_: Request, exc: StarletteHTTPException) -> JSONResponse:
        return _error_response(exc.status_code, f"http_{exc.status_code}", str(exc.detail))

    @app.exception_handler(Exception)
    async def handle_unexpected_error(_: Request, exc: Exception) -> JSONResponse:
        logger.exception("Erreur inattendue", exc_info=exc)
        return _error_response(500, "internal_error", "Erreur interne du serveur.")
