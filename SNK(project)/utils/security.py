"""
Security & Cryptographic Hashing Utilities
Provides memory-hard Scrypt password hashing (RFC 7914 / OWASP recommended),
transparent rehash detection for legacy PBKDF2/SHA256, and strict credential validation.
"""
import os
import hashlib
import hmac
import re
from typing import Tuple, Optional


# Scrypt default memory-hard parameters (OWASP 2023/2024 recommended)
SCRYPT_N = 16384  # CPU/memory cost
SCRYPT_R = 8      # Block size
SCRYPT_P = 1      # Parallelization parameter


def hash_password(password: str, salt: Optional[bytes] = None) -> str:
    """
    Hashes a plaintext password using memory-hard scrypt (RFC 7914).
    Format: "scrypt$16384$8$1$salt_hex$hash_hex"
    """
    if not password:
        raise ValueError("Password cannot be empty.")

    if salt is None:
        salt = os.urandom(16)

    key = hashlib.scrypt(
        password.encode("utf-8"),
        salt=salt,
        n=SCRYPT_N,
        r=SCRYPT_R,
        p=SCRYPT_P,
        maxmem=0,
    )

    salt_hex = salt.hex()
    key_hex = key.hex()
    return f"scrypt${SCRYPT_N}${SCRYPT_R}${SCRYPT_P}${salt_hex}${key_hex}"


def verify_password(password: str, stored_hash: str) -> bool:
    """
    Verifies a plaintext password against a stored hash string.
    Supports:
    1. Memory-hard Scrypt ("scrypt$N$R$P$salt$hash")
    2. Salted PBKDF2-HMAC-SHA256 ("salt$hash")
    3. Legacy SHA-256 (64 hex characters)
    """
    if not password or not stored_hash:
        return False

    # 1. Scrypt format
    if stored_hash.startswith("scrypt$"):
        try:
            parts = stored_hash.split("$")
            if len(parts) == 6:
                _, n_str, r_str, p_str, salt_hex, key_hex = parts
                n = int(n_str)
                r = int(r_str)
                p = int(p_str)
                salt = bytes.fromhex(salt_hex)
                expected_key = bytes.fromhex(key_hex)

                computed_key = hashlib.scrypt(
                    password.encode("utf-8"),
                    salt=salt,
                    n=n,
                    r=r,
                    p=p,
                    maxmem=0,
                )
                return hmac.compare_digest(computed_key, expected_key)
        except Exception:
            return False

    # 2. PBKDF2 format ("salt$hash")
    if "$" in stored_hash:
        try:
            salt_hex, key_hex = stored_hash.split("$", 1)
            salt = bytes.fromhex(salt_hex)
            expected_key = bytes.fromhex(key_hex)

            computed_key = hashlib.pbkdf2_hmac(
                "sha256",
                password.encode("utf-8"),
                salt,
                100000,
            )
            return hmac.compare_digest(computed_key, expected_key)
        except Exception:
            return False

    # 3. Legacy / Simple SHA256 fallback (used in initial prototype seed data)
    computed_sha256 = hashlib.sha256(password.encode("utf-8")).hexdigest()
    return hmac.compare_digest(computed_sha256, stored_hash)


def needs_rehash(stored_hash: str) -> bool:
    """
    Checks if a stored hash uses an older algorithm (PBKDF2 or SHA256)
    and should be transparently rehashed with memory-hard scrypt.
    """
    if not stored_hash:
        return True
    return not stored_hash.startswith("scrypt$")


def validate_username(username: str) -> Tuple[bool, str]:
    """Validates username format (3-30 alphanumeric characters, underscores allowed)."""
    if not username:
        return False, "Username cannot be empty."
    if len(username) < 3 or len(username) > 30:
        return False, "Username must be between 3 and 30 characters long."
    if not re.match(r"^[a-zA-Z0-9_]+$", username):
        return False, "Username can only contain letters, numbers, and underscores."
    return True, "Valid username"


def validate_password_strength(password: str) -> Tuple[bool, str]:
    """Validates password strength (min 6 characters)."""
    if not password:
        return False, "Password cannot be empty."
    if len(password) < 6:
        return False, "Password must be at least 6 characters long."
    return True, "Valid password"
