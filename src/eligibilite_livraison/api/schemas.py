"""Schémas propres à l'API (les schémas métier vivent dans ``domain``)."""

from typing import Literal

from pydantic import BaseModel, Field


class HealthStatus(BaseModel):
    status: Literal["ok"] = "ok"
    service: str = Field(examples=["eligibilite-livraison-express"])
    version: str = Field(examples=["1.0.0"])


class ReadinessStatus(BaseModel):
    status: Literal["ready", "not_ready"]
    checks: dict[str, str] = Field(examples=[{"model": "loaded", "order_store": "reachable"}])
    version: str | None = None


class OrderAccepted(BaseModel):
    order_id: str = Field(examples=["CMD-000001"])
    status: Literal["accepted"] = "accepted"


class ErrorResponse(BaseModel):
    error: str = Field(description="Code d'erreur stable", examples=["validation_error"])
    message: str = Field(description="Message pour l'humain, non contractuel")
    details: list[str] | None = None
