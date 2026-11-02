"""
Phase 2 Security Hardening Unit Tests:
- Scrypt Password Hashing & Transparent Rehash Migration
- Cryptographic Audit Log Hash Chain & Tamper Detection
- HMAC-SHA256 Backup Manifest Signing & AES-256-GCM Encryption
- Dynamic Rotating Kiosk QR TOTP Token & Replay Protection
- JWT Token Revocation & Anti-CSRF Token Validation
- Sliding Window Rate Limiting
"""
import sys
import os
import json
import time
from pathlib import Path
import pytest

BASE_DIR = Path(__file__).resolve().parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from utils.security import hash_password, verify_password, needs_rehash
from repositories.audit_repository import audit_repository, AuditRepository
from services.backup_service import backup_service
from utils.kiosk_token import (
    generate_kiosk_qr_token,
    validate_kiosk_qr_token,
    clear_replay_cache_for_testing,
)
from utils.jwt_utils import (
    create_access_token,
    decode_access_token,
    revoke_token,
    is_token_revoked,
    clear_revocation_list_for_testing,
    generate_csrf_token,
    validate_csrf_token,
)
from utils.rate_limiter import SlidingWindowRateLimiter


def test_scrypt_password_hashing_and_verification():
    """Verify Scrypt generates memory-hard salted hashes and verifies plaintext passwords."""
    pwd = "EnterprisePassword@2026!"
    scrypt_hash = hash_password(pwd)

    assert scrypt_hash.startswith("scrypt$")
    assert verify_password(pwd, scrypt_hash) is True
    assert verify_password("WrongPassword123", scrypt_hash) is False
    assert needs_rehash(scrypt_hash) is False


def test_transparent_rehash_migration():
    """Verify legacy PBKDF2 and SHA-256 hashes are detected as needing transparent rehash."""
    # Legacy PBKDF2 hash
    legacy_pbkdf2 = "31323334353637383930313233343536$18cb20a8f348be90166d435db17b182cd03c356fd8381afa395b98c8eee14b87"
    assert needs_rehash(legacy_pbkdf2) is True
    assert verify_password("Password@123", legacy_pbkdf2) is True

    # Legacy simple SHA-256 hash
    import hashlib
    legacy_sha256 = hashlib.sha256("Admin@123".encode("utf-8")).hexdigest()
    assert needs_rehash(legacy_sha256) is True
    assert verify_password("Admin@123", legacy_sha256) is True

    # After rehashing to Scrypt, needs_rehash must be False
    upgraded_hash = hash_password("Admin@123")
    assert needs_rehash(upgraded_hash) is False
    assert verify_password("Admin@123", upgraded_hash) is True


def test_audit_log_hash_chain_tamper_detection():
    """
    Verify cryptographic audit log hash chain detects unauthorized modification
    (simulating an attacker or SQL injection altering an old audit row).
    """
    repo = AuditRepository()
    # Log 3 events
    repo.log_event(user_id=1, action="TEST_ACTION_1", entity_type="USER", details="Initial event")
    repo.log_event(user_id=2, action="TEST_ACTION_2", entity_type="LEAVE", details="Second event")
    repo.log_event(user_id=3, action="TEST_ACTION_3", entity_type="SYSTEM", details="Third event")

    # Step 1: Intact chain must be 100% valid
    verification = repo.verify_chain_integrity()
    assert verification["is_valid"] is True
    assert verification["total_verified"] >= 7  # 4 initial seed + 3 new

    # Step 2: Simulate malicious SQL injection modifying details of row ID 2
    tampered_logs = [dict(entry) for entry in repo._in_memory_logs]
    for row in tampered_logs:
        if row["id"] == 2:
            row["details"] = "MALICIOUS TAMPER: Cleared disciplinary record"
            break

    tamper_result = repo.verify_chain_integrity(tampered_logs)
    assert tamper_result["is_valid"] is False
    assert tamper_result["tampered_id"] == 2
    assert "PAYLOAD_HASH_MISMATCH" in tamper_result["reason"]


def test_backup_manifest_signature_and_tamper_rejection(tmp_path):
    """Verify backup manifest HMAC-SHA256 signature generation and rejection of tampered archives."""
    backup_res = backup_service.create_backup("test_security_backup")
    zip_path = Path(backup_res["backup_path"])
    assert zip_path.exists()

    # Extract manifest.json from zip archive to verify signature
    import zipfile
    with zipfile.ZipFile(zip_path, "r") as zf:
        manifest_raw = json.loads(zf.read("manifest.json").decode("utf-8"))

    assert "signature" in manifest_raw
    assert backup_service._verify_manifest_signature(manifest_raw) is True

    # Tampering: modify total records count
    tampered_manifest = dict(manifest_raw)
    tampered_manifest["total_records"] = 999999
    assert backup_service._verify_manifest_signature(tampered_manifest) is False


def test_backup_aes_gcm_encryption_and_decryption(tmp_path):
    """Verify AES-256-GCM authenticated encryption and decryption of backup archives."""
    # Create test dummy file
    test_file = tmp_path / "faculty_pii_dump.json"
    dummy_data = b'{"employee_code": "FAC001", "salary_inr": 120000, "pan_card": "ABCDE1234F"}'
    test_file.write_bytes(dummy_data)

    pwd = "SecureInstitutionalBackupPassphrase@2026"
    enc_path = backup_service.encrypt_backup_file(test_file, password=pwd)

    assert enc_path.exists()
    assert enc_path.name.endswith(".enc")
    # Verify ciphertext is not plaintext
    enc_bytes = enc_path.read_bytes()
    assert b"ABCDE1234F" not in enc_bytes
    assert enc_bytes[:4] == b"ENCB"

    # Decrypt and verify exact byte match
    decrypted_path = tmp_path / "decrypted_dump.json"
    backup_service.decrypt_backup_file(enc_path, password=pwd, dest_path=decrypted_path)

    assert decrypted_path.exists()
    assert decrypted_path.read_bytes() == dummy_data


def test_rotating_kiosk_qr_totp_token():
    """Verify TOTP-style rotating QR token generation, time validation, and replay protection."""
    clear_replay_cache_for_testing()

    # 1. Valid token within current 30s window
    token_data = generate_kiosk_qr_token(window_seconds=30)
    token = token_data["token"]
    assert token_data["remaining_seconds"] <= 30

    res = validate_kiosk_qr_token(token, window_seconds=30, consume_on_success=True)
    assert res["valid"] is True

    # 2. Replay attack: submitting the exact same token a second time
    res_replay = validate_kiosk_qr_token(token, window_seconds=30)
    assert res_replay["valid"] is False
    assert res_replay["reason"] == "REPLAY_ATTACK_DETECTED"

    # 3. Forged token signature rejection
    parts = token.split(":")
    forged_token = f"{parts[0]}:{parts[1]}:00112233445566778899aabbccddeeff"
    res_forged = validate_kiosk_qr_token(forged_token, window_seconds=30)
    assert res_forged["valid"] is False
    assert res_forged["reason"] == "SIGNATURE_VERIFICATION_FAILED"

    # 4. Expired token rejection
    expired_window = token_data["window"] - 5  # 5 windows (150s) ago
    expired_token = f"{expired_window}:{token_data['nonce']}:fakesig"
    res_expired = validate_kiosk_qr_token(expired_token, window_seconds=30)
    assert res_expired["valid"] is False


def test_jwt_revocation_and_anti_csrf():
    """Verify JWT token revocation blocklist and anti-CSRF token verification."""
    clear_revocation_list_for_testing()

    payload = {"sub": "fac_rahul", "user_id": 3, "role": "FACULTY"}
    token = create_access_token(payload)

    # Valid token decodes successfully
    decoded = decode_access_token(token)
    assert decoded is not None
    assert decoded["sub"] == "fac_rahul"

    # Revoke token (simulate user logout)
    revoke_token(token)
    assert is_token_revoked(token) is True
    # Decoded must now return None
    assert decode_access_token(token) is None

    # Anti-CSRF Token
    sess_id = "test_session_xyz_123"
    csrf_token = generate_csrf_token(sess_id)
    assert validate_csrf_token(csrf_token, sess_id) is True
    assert validate_csrf_token("invalid_token", sess_id) is False
    assert validate_csrf_token(csrf_token, "wrong_session") is False


def test_sliding_window_rate_limiter():
    """Verify in-memory sliding window rate limiter blocks requests exceeding quota."""
    limiter = SlidingWindowRateLimiter(max_requests=3, window_seconds=10)
    client = "192.168.1.55"

    # 3 requests allowed
    ok1, rem1, _ = limiter.is_allowed(client)
    ok2, rem2, _ = limiter.is_allowed(client)
    ok3, rem3, _ = limiter.is_allowed(client)

    assert ok1 is True and rem1 == 2
    assert ok2 is True and rem2 == 1
    assert ok3 is True and rem3 == 0

    # 4th request must be blocked
    ok4, rem4, retry_after = limiter.is_allowed(client)
    assert ok4 is False
    assert rem4 == 0
    assert retry_after > 0.0
