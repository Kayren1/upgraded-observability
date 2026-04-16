from sqlalchemy import Column, Integer, String, Boolean, DateTime, Text
from sqlalchemy.orm import relationship
from datetime import datetime
from ..core.database import Base


class User(Base):
    """
    User account model.
    Represents a platform user who owns workspaces and registered systems.
    """
    __tablename__ = "users"

    # ========================================================================
    # PRIMARY KEY
    # ========================================================================
    id = Column(Integer, primary_key=True, index=True)

    # ========================================================================
    # AUTHENTICATION FIELDS
    # ========================================================================

    # Email must be unique. Used for password reset and notifications.
    email_address_for_account = Column(
        String(255),
        unique=True,
        nullable=False,
        index=True,
        comment="Unique email address. Used for login and notifications."
    )

    # Username must be unique. Usernames are used in OAuth flows and URLs.
    username_for_login = Column(
        String(100),
        unique=True,
        nullable=False,
        index=True,
        comment="Unique username used for login."
    )

    # Bcrypt hashed password. Never store plaintext passwords.
    hashed_password_from_bcrypt = Column(
        String(255),
        nullable=False,
        comment="Bcrypt-hashed password. Always verify with bcrypt, never compare raw strings."
    )

    # ========================================================================
    # PROFILE FIELDS
    # ========================================================================

    user_full_name_or_display_name = Column(
        String(255),
        nullable=True,
        comment="User's full name for display in the UI."
    )

    # ========================================================================
    # STATUS FIELDS
    # ========================================================================

    # Active users can log in. Deactivated users cannot.
    # We use soft deletes (is_active=False) instead of hard deletes to preserve data integrity.
    user_is_active_and_can_login = Column(
        Boolean,
        default=True,
        nullable=False,
        index=True,
        comment="False if user is suspended or deactivated. Cannot log in if False."
    )

    # Superusers can access all workspaces and perform admin operations.
<<<<<<< HEAD
    # TODO(kweku, 2025-04-05): Implement RBAC (role-based access control) instead of superuser flag.
=======
    # TODO(kweku, 2025-04-16): Implement RBAC (role-based access control) instead of superuser flag.
>>>>>>> 4e126db3e6dd6efc3e45c29b5713e92f2f4e74ac
    # Right now we have a simple binary flag, but proper RBAC would be better for enterprise.
    user_is_superuser_with_admin_privileges = Column(
        Boolean,
        default=False,
        nullable=False,
        comment="True if user has admin privileges. Grants access to all workspaces."
    )

    # ========================================================================
    # AUDIT FIELDS
    # ========================================================================

    # All records must have created_at and updated_at timestamps for audit trails.
    timestamp_when_user_account_was_created = Column(
        DateTime,
        default=lambda: datetime.utcnow(),
        nullable=False,
        index=True,
        comment="Timestamp when this user account was created."
    )

    timestamp_when_user_account_was_last_updated = Column(
        DateTime,
        default=lambda: datetime.utcnow(),
        onupdate=lambda: datetime.utcnow(),
        nullable=False,
        comment="Timestamp when this user's profile was last modified."
    )

    # last_login timestamp could be added here for audit purposes.
<<<<<<< HEAD
    # TODO(kweku, 2025-04-05): Add last_login_at field to track when users last accessed the platform.
=======
    # TODO(kweku, 2025-04-16): Add last_login_at field to track when users last accessed the platform.
>>>>>>> 4e126db3e6dd6efc3e45c29b5713e92f2f4e74ac
    # Useful for security audits and identifying dormant accounts.

    # ========================================================================
    # RELATIONSHIPS
    # ========================================================================

    # A user owns multiple workspaces. Workspaces are where users organize systems.
    workspaces_owned_by_this_user = relationship(
        "Workspace",
        back_populates="workspace_owner_user",
        cascade="all, delete-orphan",
        comment="Workspaces owned by this user."
    )

    # ========================================================================
    # BACKWARDS COMPATIBILITY ALIASES
    # ========================================================================
    # These properties provide shorter aliases for the verbose column names.
    # This ensures existing code that uses short names still works.
    # New code should use the explicit long names directly.

    @property
    def email(self) -> str:
        """Alias for email_address_for_account. Use explicit name in new code."""
        return self.email_address_for_account

    @property
    def username(self) -> str:
        """Alias for username_for_login. Use explicit name in new code."""
        return self.username_for_login

    @property
    def hashed_password(self) -> str:
        """Alias for hashed_password_from_bcrypt. Use explicit name in new code."""
        return self.hashed_password_from_bcrypt

    @property
    def full_name(self) -> str:
        """Alias for user_full_name_or_display_name. Use explicit name in new code."""
        return self.user_full_name_or_display_name

    @property
    def is_active(self) -> bool:
        """Alias for user_is_active_and_can_login. Use explicit name in new code."""
        return self.user_is_active_and_can_login

    @property
    def is_superuser(self) -> bool:
        """Alias for user_is_superuser_with_admin_privileges. Use explicit name in new code."""
        return self.user_is_superuser_with_admin_privileges

    @property
    def created_at(self) -> datetime:
        """Alias for timestamp_when_user_account_was_created. Use explicit name in new code."""
        return self.timestamp_when_user_account_was_created

    @property
    def updated_at(self) -> datetime:
        """Alias for timestamp_when_user_account_was_last_updated. Use explicit name in new code."""
        return self.timestamp_when_user_account_was_last_updated

    def __repr__(self) -> str:
        """String representation for debugging."""
        return f"<User id={self.id} username={self.username_for_login} email={self.email_address_for_account}>"


