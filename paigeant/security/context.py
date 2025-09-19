"""Security context and related models for Paigeant."""

from __future__ import annotations

from typing import Any, Dict, Optional

from pydantic import BaseModel, Field


class SecurityContext(BaseModel):
    """Carries authentication and authorization state for a message flow.

    The context travels alongside a :class:`~paigeant.contracts.PaigeantMessage`
    and is evaluated at each hop in the system.  Implementations are expected
    to populate the context with the on‑behalf‑of token, derived claims and
    any session or delegation metadata required for policy enforcement.
    """

    obo_token: Optional[str] = Field(default=None, description="Delegation token")
    claims: Dict[str, Any] = Field(default_factory=dict, description="Token claims")


class CanonicalMessage(BaseModel):
    """Canonical representation of a message used for signing."""

    payload: Dict[str, Any] = Field(default_factory=dict)
    headers: Dict[str, Any] = Field(default_factory=dict)


class JwsSignatureRecord(BaseModel):
    """Record of a JWS signature including headers and key id."""

    kid: str = Field(..., description="Key identifier used for signing")
    algorithm: str = Field(..., description="JWS algorithm")
    signature: str = Field(..., description="Detached JWS signature")


class SignatureEnvelope(BaseModel):
    """Envelope tying a canonical message to its signature record."""

    message: CanonicalMessage
    signature: JwsSignatureRecord
