from cryptography.fernet import Fernet
from app.config import settings
import base64
import hashlib


def _get_fernet() -> Fernet:
    key = settings.encryption_master_key
    if not key:
        derived = hashlib.sha256(settings.admin_session_secret.encode()).digest()
        key = base64.urlsafe_b64encode(derived).decode()
    if isinstance(key, str):
        key = key.encode()
    return Fernet(key)


def encrypt_credentials(plaintext: str) -> str:
    """Encrypt sensitive credentials for storage."""
    f = _get_fernet()
    return f.encrypt(plaintext.encode()).decode()


def decrypt_credentials(ciphertext: str) -> str:
    """Decrypt credentials for use in XML-RPC calls."""
    f = _get_fernet()
    return f.decrypt(ciphertext.encode()).decode()
