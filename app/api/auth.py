from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from datetime import timedelta
import logging

from ..core.database import get_database_session
from ..core.security import (
    hash_plaintext_password_with_bcrypt,
    verify_plaintext_against_bcrypt_hash,
    create_jwt_access_token,
    get_authenticated_current_user,
)
from ..core.config import settings
from ..models.user import User
from ..schemas.user import UserCreate, UserResponse, UserLogin, Token

logger = logging.getLogger(__name__)

authentication_router = APIRouter()


# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def verify_user_with_email_or_username_does_not_already_exist(
    candidate_email_address: str,
    candidate_username: str,
    database_session: Session
) -> None:
    """
    Check if a user with the given email or username already exists.
    Raises HTTPException if a duplicate is found.

    We check for both email AND username because both must be unique.
    """
    if candidate_email_address is None or candidate_email_address == "":
        raise ValueError("verify_user_with_email_or_username_does_not_already_exist: email cannot be empty")
    if candidate_username is None or candidate_username == "":
        raise ValueError("verify_user_with_email_or_username_does_not_already_exist: username cannot be empty")

    existing_user_with_same_email_or_username = database_session.query(User).filter(
        (User.email_address_for_account == candidate_email_address) |
        (User.username_for_login == candidate_username)
    ).first()

    if existing_user_with_same_email_or_username is not None:
        # Don't expose which field is duplicate for privacy reasons.
        # An attacker could use this to enumerate valid emails.
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="An account with this email or username already exists. Try logging in instead.",
        )


def verify_user_account_is_active(user_account: User) -> None:
    """
    Check if a user account is active (not suspended/deactivated).
    Raises HTTPException if the account is inactive.
    """
    if user_account is None:
        raise ValueError("verify_user_account_is_active: user cannot be None")

    if not user_account.user_is_active_and_can_login:
        logger.warning(
            f"Login attempt by inactive user account. "
            f"User ID: {user_account.id}, Email: {user_account.email_address_for_account}"
        )
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Your account has been suspended or deactivated. Contact support for help.",
        )


# ============================================================================
# ENDPOINT: POST /register
# ============================================================================

@authentication_router.post(
    "/register",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Register a new user account",
    description="Create a new user account with email, username, and password."
)
def register_new_user_account(
    user_registration_data: UserCreate,
    database_session: Session = Depends(get_database_session)
) -> UserResponse:
    """
    Create a new user account.

    Steps:
    1. Validate email/username are not already taken
    2. Hash the password with bcrypt
    3. Create the user record
    4. Return the user (without password)

    Returns: Created user with ID, email, username, etc. (no password)
    Raises: HTTPException 400 if email/username already exists
    """
    # Guard: Input data must be valid
    if user_registration_data is None:
        raise ValueError("register_new_user_account: user_registration_data cannot be None")
    if user_registration_data.email is None or user_registration_data.email == "":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email address is required."
        )
    if user_registration_data.username is None or user_registration_data.username == "":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Username is required."
        )
    if user_registration_data.password is None or len(user_registration_data.password) < 8:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Password must be at least 8 characters long."
        )

    # Guard: Email/username must not already exist
    verify_user_with_email_or_username_does_not_already_exist(
        user_registration_data.email,
        user_registration_data.username,
        database_session
    )

    # Hash the password. This is slow (intentionally) to resist brute-force attacks.
    hashed_password_bcrypt = hash_plaintext_password_with_bcrypt(user_registration_data.password)

    # Create the user record.
    newly_created_user = User(
        email_address_for_account=user_registration_data.email,
        username_for_login=user_registration_data.username,
        hashed_password_from_bcrypt=hashed_password_bcrypt,
        user_full_name_or_display_name=user_registration_data.full_name,
        user_is_active_and_can_login=True,
        user_is_superuser_with_admin_privileges=False,
    )

    # Persist to database.
    database_session.add(newly_created_user)
    database_session.commit()
    database_session.refresh(newly_created_user)

    logger.info(f"New user registered: {newly_created_user.username_for_login} ({newly_created_user.email_address_for_account})")
    return newly_created_user


# ============================================================================
# ENDPOINT: POST /login
# ============================================================================

@authentication_router.post(
    "/login",
    response_model=Token,
    summary="Login and receive JWT token",
    description="Authenticate with username and password to receive a JWT access token."
)
def login_user_and_issue_jwt_token(
    login_form_data: OAuth2PasswordRequestForm = Depends(),
    database_session: Session = Depends(get_database_session)
) -> Token:
    """
    Authenticate a user and issue a JWT access token.

    Steps:
    1. Query for user by username
    2. Verify password matches
    3. Verify account is active
    4. Create JWT token
    5. Return token + user info

    Args:
        login_form_data: OAuth2 form with username and password
        database_session: DB session

    Returns: Token object with access_token and user info
    Raises: HTTPException 401 if credentials are invalid
    """
    # Guard: Form data must exist
    if login_form_data is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Login credentials are required."
        )
    if login_form_data.username is None or login_form_data.username == "":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Username is required."
        )
    if login_form_data.password is None or login_form_data.password == "":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Password is required."
        )

    # Query for the user by username.
    user_found_in_database = database_session.query(User).filter(
        User.username_for_login == login_form_data.username
    ).first()

    # Guard: User must exist
    if user_found_in_database is None:
        logger.warning(f"Login attempt with non-existent username: {login_form_data.username}")
        # Don't say "user not found" — say "incorrect credentials" to avoid user enumeration.
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Guard: Password must match
    password_verification_succeeded = verify_plaintext_against_bcrypt_hash(
        login_form_data.password,
        user_found_in_database.hashed_password_from_bcrypt
    )

    if not password_verification_succeeded:
        logger.warning(f"Failed login attempt for user: {user_found_in_database.username_for_login}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Guard: Account must be active
    verify_user_account_is_active(user_found_in_database)

    # Create JWT access token with user ID as the subject.
    token_expiration_timedelta = timedelta(minutes=settings.JWT_ACCESS_TOKEN_EXPIRATION_MINUTES)
    newly_generated_jwt_token = create_jwt_access_token(
        payload_data_to_encode={"sub": str(user_found_in_database.id)},
        optional_expiration_delta_from_now=token_expiration_timedelta
    )

    logger.info(f"User logged in successfully: {user_found_in_database.username_for_login}")

    return Token(
        access_token=newly_generated_jwt_token,
        token_type="bearer",
        user=UserResponse.model_validate(user_found_in_database)
    )


# ============================================================================
# ENDPOINT: GET /me
# ============================================================================

@authentication_router.get(
    "/me",
    response_model=UserResponse,
    summary="Get current authenticated user",
    description="Returns the profile of the currently authenticated user."
)
def get_current_authenticated_user_profile(
    current_authenticated_user: User = Depends(get_authenticated_current_user)
) -> UserResponse:
    """
    Return the current authenticated user's profile.

    This endpoint is protected — only authenticated users can call it.
    The user is identified by the JWT token in the Authorization header.

    Args:
        current_authenticated_user: Provided by FastAPI dependency injection

    Returns: User profile (without password)
    """
    return current_authenticated_user


# ============================================================================
# ENDPOINT: POST /logout
# ============================================================================

@authentication_router.post(
    "/logout",
    summary="Logout (client-side token invalidation)",
    description="Invalidates the current JWT token on the client side."
)
def logout_current_user(
    current_authenticated_user: User = Depends(get_authenticated_current_user)
) -> dict:
    """
    Logout the current user.

    NOTE: This is a stateless logout. Since we use JWT (not sessions),
    we can't truly invalidate tokens server-side. Instead:

    1. Client must delete the token from localStorage/sessionStorage
    2. We log the logout event for audit purposes
    3. Token expiration (default 30 minutes) ensures auto-logout

    If you need true server-side logout (for security purposes),
    we'd need to implement a token blacklist in Redis.
    See: https://github.com/yourusername/upgraded-observability/issues/XXX

    Returns: Confirmation message
    """
    if current_authenticated_user is None:
        raise ValueError("logout_current_user: current_authenticated_user cannot be None")

    logger.info(f"User logged out: {current_authenticated_user.username_for_login}")
    return {
        "message": "Successfully logged out.",
        "note": "Your JWT token is still valid until it expires. Delete it from the client to complete logout."
    }


# Export router for inclusion in main API.
router = authentication_router

