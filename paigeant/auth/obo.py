import os
import time
from typing import Optional, List, Mapping

import requests
import jwt


class OboConfig:
    def __init__(self, jwks_url: str, audience: str = "", issuer: str = "", leeway: int = 0) -> None:
        self.jwks_url = jwks_url
        self.audience = audience
        self.issuer = issuer
        self.leeway = leeway

    @classmethod
    def from_env(cls) -> "OboConfig":
        return cls(
            jwks_url=os.getenv("PAIGEANT_OBO_JWKS", ""),
            audience=os.getenv("PAIGEANT_OBO_AUDIENCE", ""),
            issuer=os.getenv("PAIGEANT_OBO_ISSUER", ""),
            leeway=int(os.getenv("PAIGEANT_OBO_LEEWAY", "30")),
        )


class OboHelper:
    _jwks_cache: List[Mapping] = []
    _last_fetch: float = 0

    def __init__(self, config: Optional[OboConfig] = None) -> None:
        self.config = config or OboConfig.from_env()

    def _fetch_jwks(self) -> None:
        resp = requests.get(self.config.jwks_url, timeout=5)
        resp.raise_for_status()
        self._jwks_cache = resp.json().get("keys", [])
        self._last_fetch = time.time()

    def verify_token(self, token: str) -> Mapping:
        """Validate JWT using configured JWKS."""
        now = time.time()
        if not self._jwks_cache or now - self._last_fetch > 300:
            self._fetch_jwks()

        header = jwt.get_unverified_header(token)
        for key in self._jwks_cache:
            if key.get("kid") == header.get("kid"):
                decoded = jwt.decode(
                    token,
                    jwt.algorithms.RSAAlgorithm.from_jwk(key),
                    audience=self.config.audience,
                    issuer=self.config.issuer,
                    leeway=self.config.leeway,
                    algorithms=[header.get("alg", "RS256")],
                )
                return decoded
        raise jwt.exceptions.InvalidSignatureError("No matching JWK found.")

    def sign_message(self, payload: bytes, private_key_pem: str) -> str:
        """Placeholder for future JWS signing support."""
        raise NotImplementedError
