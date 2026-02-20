# src/coordinator/jupiter/wallet_manager.py
"""Wallet private key encryption using AES-GCM + scrypt KDF.

Pattern: Phantom wallet — encrypt with user password, never store plaintext.
Keys are decrypted in-memory for signing only, cleared on server restart.

SECURITY DESIGN:
- Private keys are encrypted at rest with AES-GCM (authenticated encryption).
- scrypt KDF (N=2^14) derives the AES key from the user's password.
- Ciphertext + salt + nonce are stored together (EncryptedKey dataclass).
- In-memory session cache (_session_keys) is cleared on every server restart — intentional.
- Private keys are NEVER logged; log statements must not reference key values.
"""

from __future__ import annotations

import base64
import logging
import secrets
from dataclasses import dataclass
from typing import Optional

logger = logging.getLogger(__name__)

# In-memory session cache: user_id -> decrypted private key (Base58 string)
# Cleared on server restart — intentional security design.
_session_keys: dict[str, str] = {}


# ---------------------------------------------------------------------------
# Data structures
# ---------------------------------------------------------------------------

@dataclass
class EncryptedKey:
    """AES-GCM encrypted private key with its KDF parameters.

    All fields are base64-encoded strings suitable for storage in SQLite.
    """

    encrypted: str  # base64-encoded AES-GCM ciphertext (includes GCM auth tag)
    salt: str       # base64-encoded scrypt salt (32 random bytes)
    nonce: str      # base64-encoded AES-GCM nonce (12 random bytes)

    def to_dict(self) -> dict:
        """Serialize to plain dict for JSON storage."""
        return {"encrypted": self.encrypted, "salt": self.salt, "nonce": self.nonce}

    @classmethod
    def from_dict(cls, d: dict) -> "EncryptedKey":
        """Deserialize from dict loaded from JSON storage."""
        return cls(encrypted=d["encrypted"], salt=d["salt"], nonce=d["nonce"])


# ---------------------------------------------------------------------------
# Encryption / Decryption
# ---------------------------------------------------------------------------

def encrypt_private_key(private_key_b58: str, password: str) -> EncryptedKey:
    """Encrypt a Solana private key with AES-256-GCM + scrypt.

    Key derivation uses scrypt with N=2^14 (interactive-class hardness).
    AES-GCM provides both confidentiality and integrity — any tampering
    with the ciphertext will cause decryption to raise InvalidTag.

    Args:
        private_key_b58: Base58-encoded Solana private key
        password: User-provided password for encryption

    Returns:
        EncryptedKey with base64-encoded ciphertext, salt, and nonce.
        Store all three fields; all are required for decryption.

    Note:
        Never log private_key_b58.
    """
    from cryptography.hazmat.primitives.ciphers.aead import AESGCM
    from cryptography.hazmat.primitives.kdf.scrypt import Scrypt

    salt = secrets.token_bytes(32)   # 256-bit salt
    nonce = secrets.token_bytes(12)  # 96-bit GCM nonce (NIST recommended)

    # Derive 32-byte (256-bit) AES key via scrypt
    # N=2^14 balances interactive-login speed vs. brute-force resistance
    kdf = Scrypt(salt=salt, length=32, n=2 ** 14, r=8, p=1)
    key = kdf.derive(password.encode("utf-8"))

    # Encrypt — AESGCM appends the 16-byte GCM authentication tag automatically
    aesgcm = AESGCM(key)
    ciphertext = aesgcm.encrypt(nonce, private_key_b58.encode("utf-8"), None)

    logger.info("Private key encrypted successfully (AES-256-GCM + scrypt)")

    return EncryptedKey(
        encrypted=base64.b64encode(ciphertext).decode(),
        salt=base64.b64encode(salt).decode(),
        nonce=base64.b64encode(nonce).decode(),
    )


def decrypt_private_key(enc_key: EncryptedKey, password: str) -> str:
    """Decrypt an AES-GCM encrypted Solana private key.

    Args:
        enc_key: EncryptedKey object (loaded from SQLite storage)
        password: User password for decryption

    Returns:
        Base58-encoded private key string

    Raises:
        ValueError: If decryption fails due to wrong password, corrupted data,
                    or tampered ciphertext (GCM authentication failure).

    Note:
        Never log the return value.
    """
    from cryptography.exceptions import InvalidTag
    from cryptography.hazmat.primitives.ciphers.aead import AESGCM
    from cryptography.hazmat.primitives.kdf.scrypt import Scrypt

    try:
        salt = base64.b64decode(enc_key.salt)
        nonce = base64.b64decode(enc_key.nonce)
        ciphertext = base64.b64decode(enc_key.encrypted)

        kdf = Scrypt(salt=salt, length=32, n=2 ** 14, r=8, p=1)
        key = kdf.derive(password.encode("utf-8"))

        aesgcm = AESGCM(key)
        plaintext = aesgcm.decrypt(nonce, ciphertext, None)
        return plaintext.decode("utf-8")

    except InvalidTag:
        # Wrong password or tampered ciphertext — do not expose details
        raise ValueError("Incorrect password or corrupted key data")
    except Exception as exc:
        raise ValueError(f"Key decryption failed: {exc}")


# ---------------------------------------------------------------------------
# In-memory session cache
# ---------------------------------------------------------------------------

def cache_session_key(user_id: str, private_key_b58: str) -> None:
    """Cache the decrypted key in memory for this server session.

    The cache survives the lifetime of the server process only.
    Restarting the server clears all cached keys — users must unlock
    their wallet again after a restart.

    Args:
        user_id: Unique user identifier (e.g. nephilim_user_id)
        private_key_b58: Decrypted Base58 private key

    Note:
        Never log private_key_b58.
    """
    _session_keys[user_id] = private_key_b58
    logger.debug(f"Session key cached for user {user_id}")


def get_session_key(user_id: str) -> Optional[str]:
    """Get the cached session key for a user (returns None if not unlocked).

    Args:
        user_id: Unique user identifier

    Returns:
        Base58 private key string, or None if wallet is locked / not found.
    """
    return _session_keys.get(user_id)


def clear_session_key(user_id: str) -> None:
    """Clear the cached session key for a user (on logout or error).

    Args:
        user_id: Unique user identifier
    """
    _session_keys.pop(user_id, None)
    logger.info(f"Session key cleared for user {user_id}")


def wallet_unlocked(user_id: str) -> bool:
    """Return True if the user's wallet is currently unlocked in this session.

    Args:
        user_id: Unique user identifier

    Returns:
        bool: True if key is cached in memory, False otherwise.
    """
    return user_id in _session_keys


# ---------------------------------------------------------------------------
# ---------------------------------------------------------------------------
# Base58 encoder (no external dependency needed)
# ---------------------------------------------------------------------------
_B58_ALPHABET = b"123456789ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz"


def _b58encode(data: bytes) -> str:
    """Base58 encode bytes (Bitcoin/Solana alphabet)."""
    n = int.from_bytes(data, "big")
    result = b""
    while n:
        n, r = divmod(n, 58)
        result = _B58_ALPHABET[r:r + 1] + result
    # Preserve leading zero bytes
    for byte in data:
        if byte == 0:
            result = _B58_ALPHABET[0:1] + result
        else:
            break
    return result.decode("ascii")


# ---------------------------------------------------------------------------
# Keypair generation
# ---------------------------------------------------------------------------

def generate_new_keypair() -> dict:
    """Generate a new Solana keypair using the solders library.

    The returned private key MUST be encrypted immediately with
    encrypt_private_key() before being stored anywhere.

    Returns:
        dict: {
            'public_address': str,   # Base58 Solana public key
            'private_key_b58': str,  # Base58 private key — encrypt immediately
        }

    Note:
        solders is optional at import time. If not installed, a placeholder
        is returned so unit tests and development environments can proceed
        without the Solana toolchain installed.

        Never log the 'private_key_b58' field from the returned dict.
    """
    try:
        from solders.keypair import Keypair  # type: ignore

        keypair = Keypair()
        # Full 64-byte keypair (secret seed + public key) in base58 — standard Phantom format
        keypair_bytes = bytes(keypair.to_bytes())
        return {
            "public_address": str(keypair.pubkey()),
            "private_key_b58": _b58encode(keypair_bytes),
        }
    except ImportError:
        logger.warning(
            "solders library not installed — returning placeholder keypair. "
            "Install with: pip install solders"
        )
        return {
            "public_address": "PLACEHOLDER_ADDRESS_" + secrets.token_hex(8),
            "private_key_b58": "PLACEHOLDER_KEY_" + secrets.token_hex(16),
        }
