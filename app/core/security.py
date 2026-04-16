from datetime import datetime, timedelta, timezone
from typing import Optional, Dict, Any
from jose import JWTError, jwt
from passlib.context import CryptContext
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session
import logging

from .config import settings
from .database import get_database_session

logger = logging.getLogger(__name__)

# ============================================================================
# PASSWORD HASHING CONFIGURATION
# ============================================================================

# Bcrypt context for secure password hashing.
# We use bcrypt because it's slow (resistant to brute force) and well-tested.
password_hashing_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# OAuth2 scheme. This tells FastAPI how to extract the JWT token from requests.
oauth2_authentication_scheme = OAuth2PasswordBearer(
    tokenUrl="/api/v1/auth/login",
    description="JWT bearer token. Obtain from /auth/login endpoint."
)


# ============================================================================
# PASSWORD UTILITIES
# ============================================================================

def hash_plaintext_password_with_bcrypt(plaintext_password: str) -> str:
    """
    Hash a plaintext password using bcrypt.
    The hash is salted and will be different each time (salts are random).
    You can verify it later with verify_password().
    """
    if plaintext_password is None or plaintext_password == "":
        raise ValueError("hash_plaintext_password_with_bcrypt: password cannot be None or empty")

    hashed_password = password_hashing_context.hash(plaintext_password)
    return hashed_password


def verify_plaintext_against_bcrypt_hash(
    plaintext_password_attempt: str,
    previously_hashed_password: str
) -> bool:
    """
    Verify a plaintext password against a previously hashed password.
    Returns True if they match, False otherwise.
    """
    if plaintext_password_attempt is None:
        raise ValueError("verify_plaintext_against_bcrypt_hash: plaintext password cannot be None")
    if previously_hashed_password is None:
        raise ValueError("verify_plaintext_against_bcrypt_hash: hashed password cannot be None")

    passwords_match = password_hashing_context.verify(
        plaintext_password_attempt,
        previously_hashed_password
    )
    return passwords_match


# ============================================================================
# JWT TOKEN UTILITIES
# ============================================================================

def create_jwt_access_token(
    payload_data_to_encode: Dict[str, Any],
    optional_expiration_delta_from_now: Optional[timedelta] = None
) -> str:
    """
    Create a signed JWT access token.

    Args:
        payload_data_to_encode: Dictionary of claims to encode (e.g., {"sub": user_id})
        optional_expiration_delta_from_now: How long until token expires. Defaults to setting.

    Returns:
        Signed JWT token string.

    Raises:
        ValueError if payload_data_to_encode is None
    """
    if payload_data_to_encode is None:
        raise ValueError("create_jwt_access_token: payload cannot be None")

    # Copy the payload to avoid modifying the original.
    payload_to_sign = payload_data_to_encode.copy()

    # Determine expiration time.
    if optional_expiration_delta_from_now is not None:
        expiration_datetime = datetime.now(timezone.utc) + optional_expiration_delta_from_now
    else:
        expiration_datetime = datetime.now(timezone.utc) + timedelta(
            minutes=settings.JWT_ACCESS_TOKEN_EXPIRATION_MINUTES
        )

    # Add expiration to the payload.
    payload_to_sign["exp"] = expiration_datetime

    # Sign the token.
    try:
        signed_jwt_token = jwt.encode(
            payload_to_sign,
            settings.JWT_SECRET_KEY_FOR_SIGNING,
            algorithm=settings.JWT_SIGNING_ALGORITHM
        )
        return signed_jwt_token
    except Exception as jwt_encoding_error:
        raise RuntimeError(
            f"Failed to encode JWT token. "
            f"Algorithm: {settings.JWT_SIGNING_ALGORITHM}. "
            f"Error: {jwt_encoding_error}"
        ) from jwt_encoding_error


def decode_jwt_token_to_payload(jwt_token_string: str) -> Optional[Dict[str, Any]]:
    """
    Decode and verify a JWT token.
    Returns the payload dictionary if valid, None if invalid or expired.
    """
    if jwt_token_string is None or jwt_token_string == "":
        logger.warning("decode_jwt_token_to_payload: received empty or None token")
        return None

    try:
        decoded_payload = jwt.decode(
            jwt_token_string,
            settings.JWT_SECRET_KEY_FOR_SIGNING,
            algorithms=[settings.JWT_SIGNING_ALGORITHM]
        )
        return decoded_payload
    except JWTError as jwt_decode_error:
        # This is expected for invalid/expired tokens, so we log at debug level.
        logger.debug(f"JWT decode failed (expected for invalid tokens): {jwt_decode_error}")
        return None
    except Exception as unexpected_jwt_error:
        logger.error(f"Unexpected error decoding JWT: {unexpected_jwt_error}")
        return None


# ============================================================================
# AUTHENTICATION DEPENDENCY FOR FASTAPI
# ============================================================================

async def get_authenticated_current_user(
    jwt_token_from_request: str = Depends(oauth2_authentication_scheme),
    database_session: Session = Depends(get_database_session)
):
    """
    FastAPI dependency that validates a JWT token and returns the authenticated user.
    Used in route handlers with: current_user: User = Depends(get_authenticated_current_user)

    This function:
    1. Extracts and validates the JWT token
    2. Queries the database for the user
    3. Raises HTTPException if authentication fails

    Raises:
        HTTPException with 401 status if token is invalid or user doesn't exist
    """
    # Guard: Token must exist
    if jwt_token_from_request is None or jwt_token_from_request == "":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="No authentication token provided. Include 'Authorization: Bearer <token>' header.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Decode the token to get the payload.
    decoded_jwt_payload = decode_jwt_token_to_payload(jwt_token_from_request)

    # Guard: Token must decode successfully
    if decoded_jwt_payload is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired authentication token. Please log in again.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Guard: Token must contain 'sub' (subject = user ID)
    user_id_from_token = decoded_jwt_payload.get("sub")
    if user_id_from_token is None:
        logger.warning("JWT token missing 'sub' claim. This indicates a malformed token.")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token format: missing user identifier. Please log in again.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Query the database for the user.
    from ..models.user import User

    try:
        authenticated_user = database_session.query(User).filter(
            User.id == int(user_id_from_token)
        ).first()
    except (ValueError, TypeError) as user_id_parsing_error:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Invalid user ID in token: {user_id_from_token}. Please log in again.",
            headers={"WWW-Authenticate": "Bearer"},
        ) from user_id_parsing_error

    # Guard: User must exist in database
    if authenticated_user is None:
        logger.warning(f"JWT token references non-existent user ID: {user_id_from_token}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found. Your account may have been deleted. Please log in again.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return authenticated_user


# Aliases for backwards compatibility.
verify_password = verify_plaintext_against_bcrypt_hash
get_password_hash = hash_plaintext_password_with_bcrypt
decode_token = decode_jwt_token_to_payload
get_current_user = get_authenticated_current_user

