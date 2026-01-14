"""
Phone number value object.
"""
import re
from dataclasses import dataclass

from shared.domain import ValueObject
from ..exceptions import InvalidPhoneNumberError


@dataclass(frozen=True)
class PhoneNumber(ValueObject):
    """Phone number value object with validation."""
    value: str

    def __post_init__(self):
        normalized = self._normalize(self.value)
        if not self._is_valid(normalized):
            raise InvalidPhoneNumberError(self.value)
        # Use object.__setattr__ for frozen dataclass
        object.__setattr__(self, 'value', normalized)

    @staticmethod
    def _normalize(phone: str) -> str:
        """Normalize phone number by removing non-numeric characters."""
        return re.sub(r'[^0-9+]', '', phone)

    @staticmethod
    def _is_valid(phone: str) -> bool:
        """Validate phone number format."""
        # Korean phone number patterns
        patterns = [
            r'^01[0-9]{8,9}$',  # Mobile: 010xxxxxxxx
            r'^\+82[0-9]{9,10}$',  # International: +82xxxxxxxxx
        ]
        return any(re.match(pattern, phone) for pattern in patterns)

    @property
    def formatted(self) -> str:
        """Get formatted phone number."""
        if self.value.startswith('+82'):
            return self.value
        # Format as 010-xxxx-xxxx
        if len(self.value) == 11:
            return f"{self.value[:3]}-{self.value[3:7]}-{self.value[7:]}"
        return self.value
