from cryptography.fernet import Fernet, InvalidToken
from app.core.config import settings


class EncryptionServiceError(Exception):
    pass


class EncryptionService:
    def __init__(self, key: str = None):
        self.key = key or settings.TOKEN_ENCRYPTION_KEY
        if not self.key:
            raise EncryptionServiceError("Token encryption key is not configured")
        try:
            self.fernet = Fernet(self.key.encode() if isinstance(self.key, str) else self.key)
        except Exception as e:
            raise EncryptionServiceError(f"Invalid encryption key: {str(e)}")

    def encrypt(self, token: str) -> str:
        if not token:
            raise EncryptionServiceError("Cannot encrypt empty token")
        try:
            encrypted = self.fernet.encrypt(token.encode())
            return encrypted.decode()
        except Exception as e:
            raise EncryptionServiceError(f"Encryption failed: {str(e)}")

    def decrypt(self, encrypted_token: str) -> str:
        if not encrypted_token:
            raise EncryptionServiceError("Cannot decrypt empty token")
        try:
            decrypted = self.fernet.decrypt(encrypted_token.encode())
            return decrypted.decode()
        except InvalidToken:
            raise EncryptionServiceError("Invalid or corrupted token")
        except Exception as e:
            raise EncryptionServiceError(f"Decryption failed: {str(e)}")
