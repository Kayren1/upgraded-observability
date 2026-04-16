from pydantic import BaseModel, EmailStr, Field
from datetime import datetime
from typing import Optional


class UserCreate(BaseModel):
    """
    Schema for user account creation (registration).
    Validates incoming data from the /register endpoint.
    """
    email: EmailStr = Field(
        ...,
        description="Unique email address. Used for login and password recovery.",
        example="user@example.com"
    )
    username: str = Field(
        ...,
        min_length=3,
        max_length=100,
        description="Unique username. Must be 3-100 characters.",
        example="alice_smith",
        pattern="^[a-zA-Z0-9_-]+$"
    )
    password: str = Field(
        ...,
        min_length=8,
        max_length=128,
        description="Password. Must be at least 8 characters. Hashed with bcrypt before storage.",
        example="SecurePassword123!"
    )
    full_name: Optional[str] = Field(
        default=None,
        max_length=255,
        description="User's full name for display. Optional.",
        example="Alice Smith"
    )


class UserLogin(BaseModel):
    """
    Schema for user login (alternative to OAuth2PasswordRequestForm).
    This is for documentation purposes; FastAPI's OAuth2PasswordRequestForm is typically used.
    """
    username: str = Field(
        ...,
        description="Username or email to log in with.",
        example="alice_smith"
    )
    password: str = Field(
        ...,
        description="Account password.",
        example="SecurePassword123!"
    )


class UserResponse(BaseModel):
    """
    Schema for user responses. This is what gets returned in API responses.
    NOTE: Never include hashed_password in responses!
    """
    id: int = Field(
        ...,
        description="Unique user ID (auto-generated).",
        example=42
    )
    email: str = Field(
        ...,
        description="User's email address.",
        example="user@example.com"
    )
    username: str = Field(
        ...,
        description="User's login username.",
        example="alice_smith"
    )
    full_name: Optional[str] = Field(
        default=None,
        description="User's full name for display.",
        example="Alice Smith"
    )
    is_active: bool = Field(
        ...,
        description="Whether the user account is active. Deactivated users cannot log in.",
        example=True
    )
    is_superuser: bool = Field(
        ...,
        description="Whether the user has admin/superuser privileges.",
        example=False
    )
    created_at: datetime = Field(
        ...,
        description="Timestamp when this user account was created.",
        example="2025-04-16T10:30:00Z"
    )

    class Config:
        from_attributes = True  # Allows conversion from SQLAlchemy models


class Token(BaseModel):
    """
    Schema for JWT token response.
    Returned by /login endpoint.
    """
    access_token: str = Field(
        ...,
        description="JWT access token. Include in Authorization header: 'Bearer <token>'",
        example="eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
    )
    token_type: str = Field(
        default="bearer",
        description="Token type. Always 'bearer' for JWT.",
        example="bearer"
    )
    user: UserResponse = Field(
        ...,
        description="Logged-in user's profile (without password)."
    )
