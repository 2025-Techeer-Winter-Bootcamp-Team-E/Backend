"""
User verified domain event.
"""
from dataclasses import dataclass
from uuid import UUID

from shared.domain import DomainEvent


@dataclass(frozen=True)
class UserVerified(DomainEvent):
    """Event raised when a user email is verified."""
    user_id: UUID
    email: str
