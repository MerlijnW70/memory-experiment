"""User data model."""

import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Optional


@dataclass
class User:
    """Represents a platform user.

    Attributes:
        user_id: Unique identifier (UUID string).
        username: Unique username, 3-32 alphanumeric chars.
        email: User's email address.
        role: One of 'user', 'admin', 'support'.
        is_active: Whether the account is active.
        created_at: Account creation timestamp.
        display_name: Optional display name.
        metadata: Arbitrary key-value metadata.
    """

    username: str
    email: str
    role: str = "user"
    is_active: bool = True
    user_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    created_at: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )
    display_name: Optional[str] = None
    metadata: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        """Serialize the user to a plain dictionary."""
        return {
            "user_id": self.user_id,
            "username": self.username,
            "email": self.email,
            "role": self.role,
            "is_active": self.is_active,
            "created_at": self.created_at,
            "display_name": self.display_name,
            "metadata": dict(self.metadata),
        }

    @classmethod
    def from_dict(cls, data: dict) -> "User":
        """Create a User from a dictionary."""
        return cls(
            user_id=data["user_id"],
            username=data["username"],
            email=data["email"],
            role=data.get("role", "user"),
            is_active=data.get("is_active", True),
            created_at=data.get(
                "created_at", datetime.now(timezone.utc).isoformat()
            ),
            display_name=data.get("display_name"),
            metadata=data.get("metadata", {}),
        )
