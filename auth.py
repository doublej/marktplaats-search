"""
Authentication and security utilities for the MarktplaatsSearch API.
Implements secure token generation, hashing, and validation.
"""

import secrets
import hashlib
import hmac
from typing import Optional
from datetime import datetime, timedelta, timezone
import os

# Security configuration constants
TOKEN_LENGTH = 32  # 256 bits of entropy
TOKEN_PREFIX = "mps_"  # Marktplaats Search prefix for easy identification
HASH_ALGORITHM = "sha256"


def generate_secure_token() -> str:
    """
    Generate a cryptographically secure API token.
    
    Returns:
        A secure random token with prefix for identification.
        Format: mps_<64 hex characters>
    """
    random_bytes = secrets.token_bytes(TOKEN_LENGTH)
    token_hex = random_bytes.hex()
    return f"{TOKEN_PREFIX}{token_hex}"


def hash_token(token: str) -> str:
    """
    Hash an API token for secure storage in the database.
    Uses SHA-256 hashing with a salt from environment.
    
    Args:
        token: The plaintext API token
        
    Returns:
        The hashed token for storage
    """
    # Get salt from environment or use a default (should be changed in production)
    salt = os.getenv("TOKEN_SALT", "change-this-salt-in-production").encode()
    
    # Use HMAC for additional security against length extension attacks
    hashed = hmac.new(salt, token.encode(), hashlib.sha256).hexdigest()
    return hashed


def verify_token(plaintext_token: str, hashed_token: str) -> bool:
    """
    Verify a plaintext token against its hashed version.
    
    Args:
        plaintext_token: The token provided by the user
        hashed_token: The hashed token from the database
        
    Returns:
        True if tokens match, False otherwise
    """
    # Hash the plaintext token and compare
    computed_hash = hash_token(plaintext_token)
    
    # Use constant-time comparison to prevent timing attacks
    return hmac.compare_digest(computed_hash, hashed_token)


def generate_user_identifier(prefix: str = "user") -> str:
    """
    Generate a unique user identifier.
    
    Args:
        prefix: Prefix for the user identifier
        
    Returns:
        A unique user identifier
    """
    random_part = secrets.token_hex(8)  # 16 characters
    return f"{prefix}_{random_part}"


def is_token_expired(created_at: datetime, expiry_days: Optional[int] = None) -> bool:
    """
    Check if a token has expired based on its creation date.
    
    Args:
        created_at: When the token was created
        expiry_days: Number of days until expiry (None = never expires)
        
    Returns:
        True if token is expired, False otherwise
    """
    if expiry_days is None:
        return False
    
    expiry_date = created_at + timedelta(days=expiry_days)
    return datetime.now(timezone.utc) > expiry_date


def validate_token_format(token: str) -> bool:
    """
    Validate that a token follows the expected format.
    Supports both new secure tokens and legacy migrated tokens.
    
    Args:
        token: The token to validate
        
    Returns:
        True if token format is valid, False otherwise
    """
    if not token:
        return False
    
    # Support new secure tokens with prefix
    if token.startswith(TOKEN_PREFIX):
        # Remove prefix and check hex format
        token_part = token[len(TOKEN_PREFIX):]
        if len(token_part) != TOKEN_LENGTH * 2:  # 2 hex chars per byte
            return False
        
        # Check if it's valid hex
        try:
            int(token_part, 16)
            return True
        except ValueError:
            return False
    
    # Support legacy tokens (for backward compatibility after migration)
    # Legacy tokens don't have the mps_ prefix
    # Accept any non-empty string as a potential legacy token
    # The actual validation will happen during hash comparison
    return True