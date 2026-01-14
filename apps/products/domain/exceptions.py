"""
Product domain exceptions.
"""
from shared.domain.exceptions import (
    DomainException,
    ValidationError,
    InsufficientStockError,
)


class InvalidProductError(ValidationError):
    """Raised when product data is invalid."""

    def __init__(self, message: str):
        super().__init__(message=message, field="product")


class InvalidSKUError(ValidationError):
    """Raised when SKU format is invalid."""

    def __init__(self, sku: str):
        super().__init__(message=f"Invalid SKU format: '{sku}'", field="sku")
        self.sku = sku


class ProductNotFoundError(DomainException):
    """Raised when a product is not found."""

    def __init__(self, identifier: str):
        super().__init__(
            message=f"Product '{identifier}' not found",
            code="PRODUCT_NOT_FOUND"
        )
        self.identifier = identifier


class CategoryNotFoundError(DomainException):
    """Raised when a category is not found."""

    def __init__(self, identifier: str):
        super().__init__(
            message=f"Category '{identifier}' not found",
            code="CATEGORY_NOT_FOUND"
        )
        self.identifier = identifier


class DuplicateSKUError(DomainException):
    """Raised when a SKU already exists."""

    def __init__(self, sku: str):
        super().__init__(
            message=f"Product with SKU '{sku}' already exists",
            code="DUPLICATE_SKU"
        )
        self.sku = sku


# Re-export for convenience
__all__ = [
    'InvalidProductError',
    'InvalidSKUError',
    'ProductNotFoundError',
    'CategoryNotFoundError',
    'DuplicateSKUError',
    'InsufficientStockError',
]
