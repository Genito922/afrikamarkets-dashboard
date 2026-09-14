"""
Chiffrement symetrique Fernet pour les credentials broker.

Usage :
    from app.core.encryption import encrypt_secret, decrypt_secret

    enc = encrypt_secret("my_api_key")   # stocké en DB
    raw = decrypt_secret(enc)            # usage runtime
"""
import base64
import os

from cryptography.fernet import Fernet

# Clé 32 octets encodée base64-url.
# En production : variable d'environnement ENCRYPTION_KEY (générée une seule fois via Fernet.generate_key())
_KEY_RAW = os.environ.get("ENCRYPTION_KEY", "")

if _KEY_RAW:
    # Accepter la clé telle quelle (déjà en base64-url 44 chars)
    _FERNET = Fernet(_KEY_RAW.encode() if isinstance(_KEY_RAW, str) else _KEY_RAW)
else:
    # Dev only : clé dérivée d'un secret fixe — JAMAIS en production
    import hashlib
    _dev_key = base64.urlsafe_b64encode(
        hashlib.sha256(b"Afrika_Markets_DEV_DO_NOT_USE_IN_PROD").digest()
    )
    _FERNET = Fernet(_dev_key)


def encrypt_secret(plaintext: str) -> str:
    """Chiffre une chaîne et retourne un token base64-url."""
    return _FERNET.encrypt(plaintext.encode()).decode()


def decrypt_secret(token: str) -> str:
    """Déchiffre un token Fernet et retourne la chaîne originale."""
    return _FERNET.decrypt(token.encode()).decode()
