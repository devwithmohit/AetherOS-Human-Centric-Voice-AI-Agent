"""Privacy controller for encryption and consent management."""

from typing import Optional, Any
import logging
import json
from cryptography.fernet import Fernet
from app.config import settings

logger = logging.getLogger(__name__)


class PrivacyController:
    """Handle encryption, anonymization, and consent checks."""

    def __init__(self) -> None:
        """Initialize privacy controller."""
        self.fernet: Optional[Fernet] = None
        self._initialize_encryption()

    def _initialize_encryption(self) -> None:
        """Initialize Fernet encryption."""
        if settings.enable_encryption and settings.encryption_key:
            try:
                self.fernet = Fernet(settings.encryption_key.encode())
                logger.info("Encryption initialized successfully")
            except Exception as e:
                logger.error(f"Failed to initialize encryption: {e}")
                logger.warning("Encryption disabled due to initialization error")
                self.fernet = None
        else:
            logger.info("Encryption disabled by configuration")

    def encrypt(self, data: Any) -> str:
        """Encrypt sensitive data.

        Args:
            data: Data to encrypt (will be JSON serialized)

        Returns:
            Encrypted string (base64 encoded)
        """
        if not self.fernet or not settings.enable_encryption:
            # Return plaintext if encryption disabled
            return json.dumps(data)

        try:
            serialized = json.dumps(data)
            encrypted = self.fernet.encrypt(serialized.encode())
            return encrypted.decode()
        except Exception as e:
            logger.error(f"Encryption failed: {e}")
            raise

    def decrypt(self, encrypted_data: str) -> Any:
        """Decrypt sensitive data.

        Args:
            encrypted_data: Encrypted string

        Returns:
            Decrypted data (parsed from JSON)
        """
        if not self.fernet or not settings.enable_encryption:
            # Assume plaintext if encryption disabled
            try:
                return json.loads(encrypted_data)
            except json.JSONDecodeError:
                return encrypted_data

        try:
            decrypted = self.fernet.decrypt(encrypted_data.encode())
            return json.loads(decrypted.decode())
        except Exception as e:
            logger.error(f"Decryption failed: {e}")
            raise

    def anonymize_pii(self, text: str) -> str:
        """Anonymize personally identifiable information.

        Args:
            text: Text containing potential PII

        Returns:
            Text with PII redacted
        """
        if not settings.anonymize_pii:
            return text

        # Basic PII patterns (in production, use spaCy or similar)
        import re

        # Email addresses
        text = re.sub(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b", "[EMAIL]", text)

        # Phone numbers (US format)
        text = re.sub(r"\b\d{3}[-.\s]?\d{3}[-.\s]?\d{4}\b", "[PHONE]", text)

        # SSN (US format)
        text = re.sub(r"\b\d{3}-\d{2}-\d{4}\b", "[SSN]", text)

        # Credit card numbers
        text = re.sub(r"\b\d{4}[\s-]?\d{4}[\s-]?\d{4}[\s-]?\d{4}\b", "[CREDIT_CARD]", text)

        # IP addresses
        text = re.sub(r"\b(?:\d{1,3}\.){3}\d{1,3}\b", "[IP_ADDRESS]", text)

        return text

    def hash_user_id(self, user_id: str) -> str:
        """Create anonymized hash of user ID.

        Args:
            user_id: User identifier

        Returns:
            SHA256 hash of user ID
        """
        import hashlib

        return hashlib.sha256(f"{user_id}{settings.secret_key}".encode()).hexdigest()

    def validate_consent(self, user_id: str, consent_type: str, consent_status: bool) -> bool:
        """Validate if operation is allowed based on consent.

        Args:
            user_id: User identifier
            consent_type: Type of consent required
            consent_status: Current consent status from database

        Returns:
            True if operation allowed, False otherwise
        """
        if not settings.require_consent:
            # Consent not enforced
            return True

        if consent_status:
            logger.debug(f"Consent granted for {user_id}: {consent_type}")
            return True

        logger.warning(f"Consent not granted for {user_id}: {consent_type}")
        return False

    def redact_sensitive_fields(
        self, data: dict[str, Any], sensitive_fields: list[str]
    ) -> dict[str, Any]:
        """Redact sensitive fields from dictionary.

        Args:
            data: Data dictionary
            sensitive_fields: List of field names to redact

        Returns:
            Data with sensitive fields redacted
        """
        redacted = data.copy()

        for field in sensitive_fields:
            if field in redacted:
                redacted[field] = "[REDACTED]"

        return redacted

    def apply_retention_policy(self, timestamp: str, retention_days: int) -> bool:
        """Check if data should be deleted based on retention policy.

        Args:
            timestamp: ISO format timestamp
            retention_days: Retention period in days

        Returns:
            True if data should be deleted, False otherwise
        """
        from datetime import datetime, timedelta

        try:
            data_time = datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
            cutoff_time = datetime.utcnow() - timedelta(days=retention_days)

            should_delete = data_time < cutoff_time

            if should_delete:
                logger.debug(
                    f"Data from {timestamp} exceeds retention policy ({retention_days} days)"
                )

            return should_delete
        except Exception as e:
            logger.error(f"Failed to apply retention policy: {e}")
            return False

    def generate_encryption_key(self) -> str:
        """Generate a new Fernet encryption key.

        Returns:
            Base64 encoded encryption key
        """
        return Fernet.generate_key().decode()

    def encrypt_field(self, value: str) -> str:
        """Encrypt a single field value.

        Args:
            value: Field value to encrypt

        Returns:
            Encrypted value
        """
        if not self.fernet or not settings.enable_encryption:
            return value

        try:
            encrypted = self.fernet.encrypt(value.encode())
            return encrypted.decode()
        except Exception as e:
            logger.error(f"Field encryption failed: {e}")
            return value

    def decrypt_field(self, encrypted_value: str) -> str:
        """Decrypt a single field value.

        Args:
            encrypted_value: Encrypted field value

        Returns:
            Decrypted value
        """
        if not self.fernet or not settings.enable_encryption:
            return encrypted_value

        try:
            decrypted = self.fernet.decrypt(encrypted_value.encode())
            return decrypted.decode()
        except Exception as e:
            logger.error(f"Field decryption failed: {e}")
            return encrypted_value


# Global instance
privacy_controller = PrivacyController()
