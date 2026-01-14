"""
Shipping info value object.
"""
from dataclasses import dataclass

from shared.domain import ValueObject


@dataclass(frozen=True)
class ShippingInfo(ValueObject):
    """Shipping information value object."""
    recipient_name: str
    phone_number: str
    address: str
    address_detail: str = ""
    postal_code: str = ""
    delivery_notes: str = ""

    @property
    def full_address(self) -> str:
        """Get the full address string."""
        parts = [self.address]
        if self.address_detail:
            parts.append(self.address_detail)
        if self.postal_code:
            parts.insert(0, f"({self.postal_code})")
        return " ".join(parts)
