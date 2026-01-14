"""
Base entity classes for DDD.
"""
from abc import ABC
from dataclasses import dataclass, field
from datetime import datetime
from typing import List
from uuid import UUID, uuid4

from .domain_event import DomainEvent


@dataclass
class BaseEntity(ABC):
    """Base entity class with identity."""
    id: UUID = field(default_factory=uuid4)
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, BaseEntity):
            return False
        return self.id == other.id

    def __hash__(self) -> int:
        return hash(self.id)

    def touch(self) -> None:
        """Update the updated_at timestamp."""
        self.updated_at = datetime.utcnow()


@dataclass
class AggregateRoot(BaseEntity):
    """Aggregate root base class with domain events."""
    _domain_events: List[DomainEvent] = field(default_factory=list, repr=False)

    def add_domain_event(self, event: DomainEvent) -> None:
        """Add a domain event to be dispatched."""
        self._domain_events.append(event)

    def clear_domain_events(self) -> List[DomainEvent]:
        """Clear and return all domain events."""
        events = self._domain_events.copy()
        self._domain_events.clear()
        return events

    @property
    def domain_events(self) -> List[DomainEvent]:
        """Get a copy of domain events."""
        return self._domain_events.copy()
