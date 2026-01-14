"""
User DTOs.
"""
from dataclasses import dataclass
from datetime import datetime
from typing import Optional
from uuid import UUID

from ...domain.entities.user import User


@dataclass
class UserCreateDTO:
    """DTO for creating a user."""
    email: str
    username: str
    password: str
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    phone_number: Optional[str] = None


@dataclass
class UserUpdateDTO:
    """DTO for updating a user."""
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    phone_number: Optional[str] = None


@dataclass
class UserDTO:
    """DTO for user output."""
    id: UUID
    email: str
    username: str
    first_name: str
    last_name: str
    phone_number: Optional[str]
    is_active: bool
    is_verified: bool
    created_at: datetime
    updated_at: datetime

    @classmethod
    def from_entity(cls, user: User) -> 'UserDTO':
        """Create DTO from entity."""
        return cls(
            id=user.id,
            email=user.email.value,
            username=user.username,
            first_name=user.first_name,
            last_name=user.last_name,
            phone_number=user.phone_number.value if user.phone_number else None,
            is_active=user.is_active,
            is_verified=user.is_verified,
            created_at=user.created_at,
            updated_at=user.updated_at,
        )
