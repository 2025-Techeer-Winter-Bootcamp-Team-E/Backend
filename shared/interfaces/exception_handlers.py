"""
Custom exception handlers for DRF.
"""
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import exception_handler

from shared.domain.exceptions import (
    DomainException,
    EntityNotFoundError,
    ValidationError,
    BusinessRuleViolationError,
    InsufficientStockError,
    InvalidOperationError,
)


def custom_exception_handler(exc, context):
    """Handle custom domain exceptions."""
    # Call REST framework's default exception handler first
    response = exception_handler(exc, context)

    # Handle domain exceptions
    if isinstance(exc, EntityNotFoundError):
        return Response(
            {
                'error': exc.message,
                'code': exc.code,
                'entity': exc.entity_name,
                'entity_id': exc.entity_id,
            },
            status=status.HTTP_404_NOT_FOUND,
        )

    if isinstance(exc, ValidationError):
        return Response(
            {
                'error': exc.message,
                'code': exc.code,
                'field': exc.field,
            },
            status=status.HTTP_400_BAD_REQUEST,
        )

    if isinstance(exc, InsufficientStockError):
        return Response(
            {
                'error': exc.message,
                'code': exc.code,
                'product_id': exc.product_id,
                'requested': exc.requested,
                'available': exc.available,
            },
            status=status.HTTP_400_BAD_REQUEST,
        )

    if isinstance(exc, BusinessRuleViolationError):
        return Response(
            {
                'error': exc.message,
                'code': exc.code,
                'rule': exc.rule,
            },
            status=status.HTTP_422_UNPROCESSABLE_ENTITY,
        )

    if isinstance(exc, InvalidOperationError):
        return Response(
            {
                'error': exc.message,
                'code': exc.code,
                'operation': exc.operation,
                'state': exc.state,
            },
            status=status.HTTP_409_CONFLICT,
        )

    if isinstance(exc, DomainException):
        return Response(
            {
                'error': exc.message,
                'code': exc.code,
            },
            status=status.HTTP_400_BAD_REQUEST,
        )

    return response
