"""
Cryptographic JSON Web Token (JWT) & CSRF Security Utilities
RFC 7519 Compliant HMAC-SHA256 Token Encoder and Decoder.
Zero external dependencies (uses standard library hmac, hashlib, base64, json).
Provides signed bearer tokens, refresh tokens, token revocation, and double-submit anti-CSRF protection.
"""
import hmac
import hashlib
import base64
import json
import time
import os
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List, Set

from config.settings import settings
from utils.logger import get_logger

logger = get_logger("utils.jwt_utils")

# Default secret key from settings or secure institutional seed
JWT_SECRET = getattr(settings, "SECRET_KEY", "faculty_erp_jwt_institutional_secret_2026_key")
JWT_ALGORITHM = "HS256"
DEFAULT_ACCESS_EXPIRY_MINUTES = 30
DEFAULT_REFRESH_EXPIRY_DAYS = 7
CSRF_SECRET = getattr(settings, "CSRF_SECRET_KEY", f"{JWT_SECRET}_csrf_secret_salt")

# In-memory revocation blocklist for logged-out / revoked JWT tokens
REVOKED_TOKENS: Set[str] = set()


def revoke_token(token: str):
    """Adds a token to the active revocation blocklist."""
    if token:
        REVOKED_TOKENS.add(token.strip())
        logger.info("JWT token successfully added to revocation blocklist.")


def is_token_revoked(token: str) -> bool:
    """Checks if a token has been explicitly revoked."""
    if not token:
        return True
    return token.strip() in REVOKED_TOKENS


def clear_revocation_list_for_testing():
    """Resets the revocation blocklist."""
    REVOKED_TOKENS.clear()


def _base64url_encode(data: bytes) -> str:
    """Encodes bytes into URL-safe base64 string without trailing padding."""
    return base64.urlsafe_b64encode(data).decode("utf-8").rstrip("=")


def _base64url_decode(encoded: str) -> bytes:
    """Decodes URL-safe base64 string, restoring required padding."""
    rem = len(encoded) % 4
    if rem > 0:
        encoded += "=" * (4 - rem)
    return base64.urlsafe_b64decode(encoded.encode("utf-8"))


def create_access_token(
    payload: Dict[str, Any],
    expires_delta: Optional[timedelta] = None,
    secret_key: str = JWT_SECRET,
) -> str:
    """
    Creates a signed HMAC-SHA256 short-lived access token.
    Adds standard 'iat' (issued at), 'exp' (expiration), and 'type': 'access' claims.
    """
    header = {"alg": JWT_ALGORITHM, "typ": "JWT"}
    now = int(time.time())

    token_payload = dict(payload)
    token_payload["iat"] = now
    token_payload["type"] = "access"
    if "exp" not in token_payload:
        exp_delta = expires_delta or timedelta(minutes=DEFAULT_ACCESS_EXPIRY_MINUTES)
        token_payload["exp"] = now + int(exp_delta.total_seconds())

    # Encode Header & Payload
    header_json = json.dumps(header, separators=(",", ":"), sort_keys=True).encode("utf-8")
    payload_json = json.dumps(token_payload, separators=(",", ":"), sort_keys=True).encode("utf-8")

    header_b64 = _base64url_encode(header_json)
    payload_b64 = _base64url_encode(payload_json)

    signing_input = f"{header_b64}.{payload_b64}".encode("utf-8")

    # Generate HMAC-SHA256 signature
    signature = hmac.new(secret_key.encode("utf-8"), signing_input, hashlib.sha256).digest()
    sig_b64 = _base64url_encode(signature)

    return f"{header_b64}.{payload_b64}.{sig_b64}"


def create_refresh_token(
    payload: Dict[str, Any],
    expires_delta: Optional[timedelta] = None,
    secret_key: str = JWT_SECRET,
) -> str:
    """
    Creates a long-lived rotating refresh token.
    Adds 'type': 'refresh' claim and random jti nonce.
    """
    header = {"alg": JWT_ALGORITHM, "typ": "JWT"}
    now = int(time.time())

    token_payload = dict(payload)
    token_payload["iat"] = now
    token_payload["type"] = "refresh"
    token_payload["jti"] = os.urandom(8).hex()

    exp_delta = expires_delta or timedelta(days=DEFAULT_REFRESH_EXPIRY_DAYS)
    token_payload["exp"] = now + int(exp_delta.total_seconds())

    header_json = json.dumps(header, separators=(",", ":"), sort_keys=True).encode("utf-8")
    payload_json = json.dumps(token_payload, separators=(",", ":"), sort_keys=True).encode("utf-8")

    header_b64 = _base64url_encode(header_json)
    payload_b64 = _base64url_encode(payload_json)

    signing_input = f"{header_b64}.{payload_b64}".encode("utf-8")
    signature = hmac.new(secret_key.encode("utf-8"), signing_input, hashlib.sha256).digest()
    sig_b64 = _base64url_encode(signature)

    return f"{header_b64}.{payload_b64}.{sig_b64}"


def decode_access_token(
    token: str,
    secret_key: str = JWT_SECRET,
    verify_exp: bool = True,
) -> Optional[Dict[str, Any]]:
    """
    Decodes and verifies a JWT token.
    Validates HMAC signature, checks expiration, and enforces revocation blocklist.
    Returns payload dictionary if valid, None if invalid, expired, or revoked.
    """
    if not token or not isinstance(token, str):
        return None

    cleaned_token = token.strip()
    if is_token_revoked(cleaned_token):
        logger.warning("Rejected token: Token is present on revocation blocklist.")
        return None

    parts = cleaned_token.split(".")
    if len(parts) != 3:
        logger.warning("Invalid JWT structure: Token does not contain 3 segments.")
        return None

    header_b64, payload_b64, sig_b64 = parts

    try:
        signing_input = f"{header_b64}.{payload_b64}".encode("utf-8")
        expected_sig = hmac.new(secret_key.encode("utf-8"), signing_input, hashlib.sha256).digest()
        provided_sig = _base64url_decode(sig_b64)

        # Constant-time comparison prevents timing attacks
        if not hmac.compare_digest(expected_sig, provided_sig):
            logger.warning("JWT signature verification failed.")
            return None

        payload_bytes = _base64url_decode(payload_b64)
        payload = json.loads(payload_bytes.decode("utf-8"))

        # Verify expiration
        if verify_exp and "exp" in payload:
            now = int(time.time())
            if now > payload["exp"]:
                logger.warning(f"JWT has expired: exp={payload['exp']} < now={now}")
                return None

        return payload

    except Exception as exc:
        logger.warning(f"JWT decode error: {exc}")
        return None


def extract_token_from_request(request_headers: dict, request_cookies: dict, cookie_key: str) -> Optional[str]:
    """
    Extracts JWT from Bearer Authorization header or specified cookie.
    Priority: Authorization Bearer header -> HTTP Cookie.
    """
    # 1. Check Authorization: Bearer <token>
    auth_header = request_headers.get("authorization") or request_headers.get("Authorization")
    if auth_header and auth_header.strip().lower().startswith("bearer "):
        return auth_header.strip()[7:].strip()

    # 2. Check Cookie
    return request_cookies.get(cookie_key)


# -------------------------------------------------------------
# Anti-CSRF Token Engine (Double-Submit HMAC Pattern)
# -------------------------------------------------------------

def generate_csrf_token(session_id: str) -> str:
    """
    Generates an anti-CSRF token bound to a session identifier using HMAC-SHA256.
    """
    if not session_id:
        session_id = os.urandom(16).hex()
    msg = f"csrf:{session_id}".encode("utf-8")
    sig = hmac.new(CSRF_SECRET.encode("utf-8"), msg, hashlib.sha256).hexdigest()
    return f"{session_id}:{sig}"


def validate_csrf_token(token: str, session_id: str) -> bool:
    """
    Validates anti-CSRF token against the given session identifier.
    """
    if not token or not session_id:
        return False
    parts = token.strip().split(":")
    if len(parts) != 2:
        return False
    token_sess, provided_sig = parts
    if token_sess != session_id:
        return False
    expected_token = generate_csrf_token(session_id)
    return hmac.compare_digest(token.strip(), expected_token)
