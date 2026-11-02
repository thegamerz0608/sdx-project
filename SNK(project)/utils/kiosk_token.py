"""
Dynamic TOTP-Style Rotating Kiosk QR Token Engine
Generates time-bound, cryptographically signed one-time QR tokens (15-30s rotation window)
with HMAC-SHA256 verification and single-use replay protection.
"""
import os
import time
import hmac
import hashlib
from typing import Dict, Any, Optional

from config.settings import settings
from utils.logger import get_logger

logger = get_logger("utils.kiosk_token")

# Secret key for kiosk token signing
KIOSK_SECRET = getattr(settings, "KIOSK_TOKEN_SECRET", getattr(settings, "SECRET_KEY", "kiosk_totp_qr_secret_key_2026"))

# In-memory replay cache: maps token -> consumed_at timestamp
_USED_KIOSK_TOKENS: Dict[str, float] = {}


def _cleanup_expired_tokens(max_age_seconds: int = 120):
    """Evicts tokens older than retention window from replay cache."""
    now = time.time()
    expired_keys = [t for t, ts in _USED_KIOSK_TOKENS.items() if now - ts > max_age_seconds]
    for k in expired_keys:
        _USED_KIOSK_TOKENS.pop(k, None)


def generate_kiosk_qr_token(window_seconds: int = 30) -> Dict[str, Any]:
    """
    Generates a time-rotating, HMAC-signed token for kiosk QR code display.
    """
    now = time.time()
    window = int(now) // window_seconds
    nonce = os.urandom(8).hex()

    msg = f"{window}:{nonce}".encode("utf-8")
    sig = hmac.new(KIOSK_SECRET.encode("utf-8"), msg, hashlib.sha256).hexdigest()

    token = f"{window}:{nonce}:{sig}"
    remaining = int(((window + 1) * window_seconds) - now)

    return {
        "token": token,
        "window": window,
        "nonce": nonce,
        "window_seconds": window_seconds,
        "remaining_seconds": max(1, remaining),
    }


def validate_kiosk_qr_token(
    token: str,
    max_drift_windows: int = 1,
    window_seconds: int = 30,
    consume_on_success: bool = True,
) -> Dict[str, Any]:
    """
    Validates a submitted Kiosk QR token against time window, HMAC signature, and replay cache.
    """
    _cleanup_expired_tokens(max_age_seconds=window_seconds * 3)

    if not token or not isinstance(token, str):
        return {"valid": False, "reason": "TOKEN_EMPTY_OR_INVALID_TYPE"}

    parts = token.strip().split(":")
    if len(parts) != 3:
        return {"valid": False, "reason": "TOKEN_FORMAT_INVALID"}

    window_str, nonce, provided_sig = parts
    try:
        token_window = int(window_str)
    except ValueError:
        return {"valid": False, "reason": "TOKEN_WINDOW_NOT_INTEGER"}

    # 1. Signature check
    expected_msg = f"{token_window}:{nonce}".encode("utf-8")
    expected_sig = hmac.new(KIOSK_SECRET.encode("utf-8"), expected_msg, hashlib.sha256).hexdigest()
    if not hmac.compare_digest(provided_sig, expected_sig):
        return {"valid": False, "reason": "SIGNATURE_VERIFICATION_FAILED"}

    # 2. Time window validity check
    now = time.time()
    current_window = int(now) // window_seconds

    if token_window < (current_window - max_drift_windows):
        return {"valid": False, "reason": "TOKEN_EXPIRED"}
    if token_window > (current_window + 1):
        return {"valid": False, "reason": "TOKEN_FUTURE_WINDOW"}

    # 3. Single-use replay protection check
    if token in _USED_KIOSK_TOKENS:
        return {"valid": False, "reason": "REPLAY_ATTACK_DETECTED"}

    if consume_on_success:
        _USED_KIOSK_TOKENS[token] = now

    return {
        "valid": True,
        "window": token_window,
        "nonce": nonce,
        "reason": "TOKEN_VALID",
    }


def clear_replay_cache_for_testing():
    """Resets the used tokens replay cache."""
    _USED_KIOSK_TOKENS.clear()
