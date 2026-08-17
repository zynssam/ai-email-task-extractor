"""
Fernet symmetric encryption for sensitive data (OAuth tokens).

Usage:
    from crypto import encrypt_token, decrypt_token

    ciphertext = encrypt_token(oauth_access_token)
    plaintext  = decrypt_token(ciphertext)
"""
import os
from cryptography.fernet import Fernet
from dotenv import load_dotenv

load_dotenv()

ENCRYPTION_KEY = os.getenv("ENCRYPTION_KEY")
if not ENCRYPTION_KEY:
    raise RuntimeError(
        "ENCRYPTION_KEY environment variable is required. "
        "Generate one with: python -c \"from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())\""
    )

_fernet = Fernet(ENCRYPTION_KEY.encode("utf-8"))


def encrypt_token(plaintext: str) -> str:
    """Encrypt an OAuth token for safe database storage."""
    return _fernet.encrypt(plaintext.encode("utf-8")).decode("utf-8")


def decrypt_token(ciphertext: str) -> str:
    """Decrypt an OAuth token retrieved from the database."""
    return _fernet.decrypt(ciphertext.encode("utf-8")).decode("utf-8")
