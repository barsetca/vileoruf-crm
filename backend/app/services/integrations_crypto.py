from cryptography.fernet import Fernet, InvalidToken
from backend.app.core.config import get_integration_security_settings
class IntegrationTokenError(ValueError): pass
def _fernet():
    key=get_integration_security_settings().integration_token_encryption_key
    if key is None: raise IntegrationTokenError("Integration token encryption is not configured")
    try: return Fernet(key.get_secret_value().encode())
    except (ValueError,TypeError) as error: raise IntegrationTokenError("Integration token encryption is invalid") from error
def encrypt_token_payload(payload: bytes)->str: return _fernet().encrypt(payload).decode()
def decrypt_token_payload(ciphertext: str)->bytes:
    try:return _fernet().decrypt(ciphertext.encode())
    except InvalidToken as error: raise IntegrationTokenError("Integration token payload is invalid") from error
