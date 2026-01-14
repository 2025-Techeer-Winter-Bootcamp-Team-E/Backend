"""
Order number value object.
"""
import random
import string
from dataclasses import dataclass
from datetime import datetime

from shared.domain import ValueObject


@dataclass(frozen=True)
class OrderNumber(ValueObject):
    """Order number value object."""
    value: str

    @classmethod
    def generate(cls) -> 'OrderNumber':
        """Generate a new order number."""
        date_part = datetime.now().strftime("%Y%m%d")
        random_part = ''.join(random.choices(string.ascii_uppercase + string.digits, k=6))
        return cls(value=f"ORD-{date_part}-{random_part}")
