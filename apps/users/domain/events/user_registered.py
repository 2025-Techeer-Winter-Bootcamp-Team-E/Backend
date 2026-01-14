"""
User registered domain event.
"""
from dataclasses import dataclass
from uuid import UUID

from shared.domain import DomainEvent


@dataclass(frozen=True)
class UserRegistered(DomainEvent):
    """Event raised when a new user is registered."""
    user_id: UUID
    email: str
    username: str
