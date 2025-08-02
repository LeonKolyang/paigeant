import jwt
import json
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.primitives import serialization

from paigeant.auth.obo import OboHelper, OboConfig


def generate_keys():
    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    private_pem = key.private_bytes(
        serialization.Encoding.PEM,
        serialization.PrivateFormat.PKCS8,
        serialization.NoEncryption(),
    )
    public_jwk = jwt.algorithms.RSAAlgorithm.to_jwk(key.public_key())
    jwk_dict = json.loads(public_jwk)
    jwk_dict["kid"] = "test"
    jwk_dict["use"] = "sig"
    jwk_dict["alg"] = "RS256"
    return key, jwk_dict, private_pem


def test_obo_forward_and_claims(monkeypatch):
    key, jwk_dict, private_pem = generate_keys()
    token = jwt.encode(
        {"sub": "alice", "aud": "worker", "iss": "https://idp/"},
        private_pem,
        algorithm="RS256",
        headers={"kid": "test"},
    )

    jwks = {"keys": [jwk_dict]}

    class Resp:
        def __init__(self):
            self.status_code = 200

        def raise_for_status(self):
            pass

        def json(self):
            return jwks

    def fake_get(url, timeout=5):
        return Resp()

    monkeypatch.setattr("requests.get", fake_get)

    helper = OboHelper(OboConfig(jwks_url="http://idp/jwks", audience="worker", issuer="https://idp/"))
    claims = helper.verify_token(token)
    assert claims["sub"] == "alice"
