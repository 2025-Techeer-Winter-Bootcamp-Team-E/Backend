"""
SKU value object.
"""
import re
from dataclasses import dataclass

from shared.domain import ValueObject
from ..exceptions import InvalidSKUError


@dataclass(frozen=True)
class SKU(ValueObject):
    """Stock Keeping Unit value object."""
    value: str

    def __post_init__(self):
        normalized = self.value.upper().strip()
        if not self._is_valid(normalized):
            raise InvalidSKUError(self.value)
        object.__setattr__(self, 'value', normalized)

    @staticmethod
    def _is_valid(sku: str) -> bool:
        """Validate SKU format (alphanumeric with dashes)."""
        pattern = r'^[A-Z0-9][A-Z0-9\-]{2,49}$'
        return bool(re.match(pattern, sku))
