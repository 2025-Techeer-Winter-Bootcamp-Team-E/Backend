"""
Email value object.
"""
import re
from dataclasses import dataclass

from shared.domain import ValueObject
from ..exceptions import InvalidEmailError


@dataclass(frozen=True)
class Email(ValueObject):
    """Email value object with validation."""
    value: str

    def __post_init__(self):
        if not self._is_valid(self.value):
            raise InvalidEmailError(self.value)

    @staticmethod
    def _is_valid(email: str) -> bool:
        """Validate email format."""
        pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        return bool(re.match(pattern, email))

    @property
    def domain(self) -> str:
        """Get the email domain."""
        return self.value.split('@')[1]

    @property
    def local_part(self) -> str:
        """Get the local part of the email."""
        return self.value.split('@')[0]
