"""
User entity (Aggregate Root).
"""
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional
from uuid import UUID

from shared.domain import AggregateRoot
from ..value_objects.email import Email
from ..value_objects.phone_number import PhoneNumber
from ..events.user_registered import UserRegistered
from ..events.user_verified import UserVerified
from ..exceptions import UserAlreadyVerifiedError


@dataclass
class User(AggregateRoot):
    """User entity representing a registered user."""
    email: Email
    username: str
    hashed_password: str
    phone_number: Optional[PhoneNumber] = None
    first_name: str = ""
    last_name: str = ""
    is_active: bool = True
    is_verified: bool = False
    is_staff: bool = False
    is_superuser: bool = False
    last_login: Optional[datetime] = None

    @classmethod
    def create(
        cls,
        email: str,
        username: str,
        hashed_password: str,
        first_name: str = "",
        last_name: str = "",
        phone_number: Optional[str] = None,
    ) -> 'User':
        """Factory method to create a new user."""
        user = cls(
            email=Email(value=email),
            username=username,
            hashed_password=hashed_password,
            first_name=first_name,
            last_name=last_name,
            phone_number=PhoneNumber(value=phone_number) if phone_number else None,
        )
        user.add_domain_event(
            UserRegistered(
                user_id=user.id,
                email=email,
                username=username,
            )
        )
        return user

    def verify(self) -> None:
        """Mark the user as verified."""
        if self.is_verified:
            raise UserAlreadyVerifiedError(str(self.id))
        self.is_verified = True
        self.touch()
        self.add_domain_event(
            UserVerified(user_id=self.id, email=self.email.value)
        )

    def deactivate(self) -> None:
        """Deactivate the user account."""
        self.is_active = False
        self.touch()

    def activate(self) -> None:
        """Activate the user account."""
        self.is_active = True
        self.touch()

    def update_profile(
        self,
        first_name: Optional[str] = None,
        last_name: Optional[str] = None,
        phone_number: Optional[str] = None,
    ) -> None:
        """Update user profile information."""
        if first_name is not None:
            self.first_name = first_name
        if last_name is not None:
            self.last_name = last_name
        if phone_number is not None:
            self.phone_number = PhoneNumber(value=phone_number)
        self.touch()

    def update_password(self, hashed_password: str) -> None:
        """Update the user's password."""
        self.hashed_password = hashed_password
        self.touch()

    def record_login(self) -> None:
        """Record a successful login."""
        self.last_login = datetime.utcnow()
        self.touch()

    @property
    def full_name(self) -> str:
        """Get the user's full name."""
        return f"{self.first_name} {self.last_name}".strip()
