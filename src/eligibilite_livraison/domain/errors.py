"""Erreurs métier. Chaque classe porte un code stable, exploitable côté client."""


class DomainError(Exception):
    """Racine des erreurs attendues de l'application."""

    code = "domain_error"


class ConfigurationError(DomainError):
    code = "configuration_error"


class DataQualityError(DomainError):
    code = "data_quality_error"


class OrderNotFoundError(DomainError):
    code = "order_not_found"


class DuplicateOrderError(DomainError):
    code = "duplicate_order"


class StorageError(DomainError):
    """Le support de stockage a échoué (disque, base de données...)."""

    code = "storage_error"


class InvalidModelVersionError(DomainError):
    code = "invalid_model_version"


class ModelAlreadyExistsError(DomainError):
    code = "model_already_exists"


class ModelUnavailableError(DomainError):
    """Aucun modèle utilisable pour répondre à une prédiction."""

    code = "model_unavailable"


class ModelNotFoundError(ModelUnavailableError):
    code = "model_not_found"
