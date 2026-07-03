from uuid import UUID

import jwt
import requests
from fastapi import Header, HTTPException

from app.core.config import settings

_JWKS_URL = f"{settings.SUPABASE_URL}/auth/v1/.well-known/jwks.json"
_ALGORITHM = "ES256"
_AUDIENCE = "authenticated"

# Module-level in-memory cache of {kid: PyJWK}, same pattern as
# price_service.py's module-level cache. Refetched when a token's kid is
# unseen (first request, or Supabase rotated its signing key) or when a
# signature verification fails against the cached key (key-rotation retry).
_jwks_cache: dict = {}


def _fetch_jwks() -> dict:
    response = requests.get(_JWKS_URL, timeout=5)
    response.raise_for_status()
    data = response.json()
    return {
        key_dict["kid"]: jwt.PyJWK.from_dict(key_dict)
        for key_dict in data.get("keys", [])
        if "kid" in key_dict
    }


def _get_signing_key(kid: str, force_refresh: bool = False):
    global _jwks_cache
    if force_refresh or kid not in _jwks_cache:
        try:
            _jwks_cache = _fetch_jwks()
        except (requests.RequestException, ValueError):
            return None
    return _jwks_cache.get(kid)


def get_current_user_id(authorization: str = Header(None)) -> UUID:
    """
    FastAPI dependency that verifies a Supabase-issued JWT (ES256 / ECC
    P-256) from the Authorization header and returns the authenticated
    user's UUID (the token's 'sub' claim).

    Every failure mode returns 401, never 500 — a malformed, expired,
    wrong-audience, or badly-signed token is a client auth failure, not a
    server error.
    """
    unauthorized = HTTPException(
        status_code=401,
        detail="Invalid or missing authentication token.",
        headers={"WWW-Authenticate": "Bearer"},
    )

    if not authorization or not authorization.startswith("Bearer "):
        raise unauthorized
    token = authorization[len("Bearer "):]

    try:
        kid = jwt.get_unverified_header(token).get("kid")
    except jwt.InvalidTokenError:
        raise unauthorized
    if not kid:
        raise unauthorized

    signing_key = _get_signing_key(kid)
    if signing_key is None:
        raise unauthorized

    try:
        payload = jwt.decode(
            token,
            key=signing_key.key,
            algorithms=[_ALGORITHM],
            audience=_AUDIENCE,
        )
    except jwt.InvalidSignatureError:
        # Key rotation: the cached key for this kid no longer verifies.
        # Force one JWKS refetch and retry exactly once.
        signing_key = _get_signing_key(kid, force_refresh=True)
        if signing_key is None:
            raise unauthorized
        try:
            payload = jwt.decode(
                token,
                key=signing_key.key,
                algorithms=[_ALGORITHM],
                audience=_AUDIENCE,
            )
        except jwt.PyJWTError:
            raise unauthorized
    except jwt.PyJWTError:
        raise unauthorized

    sub = payload.get("sub")
    if not sub:
        raise unauthorized
    try:
        return UUID(sub)
    except ValueError:
        raise unauthorized
