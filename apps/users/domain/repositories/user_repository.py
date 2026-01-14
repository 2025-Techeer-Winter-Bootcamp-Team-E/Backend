"""
User repository interface.
"""
from abc import ABC, abstractmethod
from typing import List, Optional
from uuid import UUID

from ..entities.user import User


class UserRepository(ABC):
    """Abstract repository for User aggregate."""

    @abstractmethod
    def save(self, user: User) -> User:
        """Save a user."""
        pass

    @abstractmethod
    def find_by_id(self, user_id: UUID) -> Optional[User]:
        """Find a user by ID."""
        pass

    @abstractmethod
    def find_by_email(self, email: str) -> Optional[User]:
        """Find a user by email."""
        pass

    @abstractmethod
    def find_by_username(self, username: str) -> Optional[User]:
        """Find a user by username."""
        pass

    @abstractmethod
    def exists_by_email(self, email: str) -> bool:
        """Check if a user exists with the given email."""
        pass

    @abstractmethod
    def exists_by_username(self, username: str) -> bool:
        """Check if a user exists with the given username."""
        pass

    @abstractmethod
    def find_all(
        self,
        is_active: Optional[bool] = None,
        offset: int = 0,
        limit: int = 20,
    ) -> List[User]:
        """Find all users with optional filters."""
        pass

    @abstractmethod
    def delete(self, user_id: UUID) -> bool:
        """Delete a user by ID."""
        pass
