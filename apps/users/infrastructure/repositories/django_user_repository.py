"""
Django ORM implementation of UserRepository.
"""
from typing import List, Optional
from uuid import UUID

from django.db import transaction

from ...domain.entities.user import User
from ...domain.repositories.user_repository import UserRepository
from ...domain.value_objects.email import Email
from ...domain.value_objects.phone_number import PhoneNumber
from ..models.user_model import UserModel


class DjangoUserRepository(UserRepository):
    """Django ORM based user repository implementation."""

    def save(self, user: User) -> User:
        """Save a user entity."""
        with transaction.atomic():
            model, created = UserModel.objects.update_or_create(
                id=user.id,
                defaults={
                    'email': user.email.value,
                    'username': user.username,
                    'password': user.hashed_password,
                    'first_name': user.first_name,
                    'last_name': user.last_name,
                    'phone_number': user.phone_number.value if user.phone_number else None,
                    'is_active': user.is_active,
                    'is_verified': user.is_verified,
                    'is_staff': user.is_staff,
                    'is_superuser': user.is_superuser,
                    'last_login': user.last_login,
                }
            )
            return self._to_entity(model)

    def find_by_id(self, user_id: UUID) -> Optional[User]:
        """Find a user by ID."""
        try:
            model = UserModel.objects.get(id=user_id)
            return self._to_entity(model)
        except UserModel.DoesNotExist:
            return None

    def find_by_email(self, email: str) -> Optional[User]:
        """Find a user by email."""
        try:
            model = UserModel.objects.get(email=email)
            return self._to_entity(model)
        except UserModel.DoesNotExist:
            return None

    def find_by_username(self, username: str) -> Optional[User]:
        """Find a user by username."""
        try:
            model = UserModel.objects.get(username=username)
            return self._to_entity(model)
        except UserModel.DoesNotExist:
            return None

    def exists_by_email(self, email: str) -> bool:
        """Check if a user exists with the given email."""
        return UserModel.objects.filter(email=email).exists()

    def exists_by_username(self, username: str) -> bool:
        """Check if a user exists with the given username."""
        return UserModel.objects.filter(username=username).exists()

    def find_all(
        self,
        is_active: Optional[bool] = None,
        offset: int = 0,
        limit: int = 20,
    ) -> List[User]:
        """Find all users with optional filters."""
        queryset = UserModel.objects.all()
        if is_active is not None:
            queryset = queryset.filter(is_active=is_active)
        models = queryset.order_by('-created_at')[offset:offset + limit]
        return [self._to_entity(model) for model in models]

    def delete(self, user_id: UUID) -> bool:
        """Delete a user by ID."""
        deleted, _ = UserModel.objects.filter(id=user_id).delete()
        return deleted > 0

    def _to_entity(self, model: UserModel) -> User:
        """Convert Django model to domain entity."""
        return User(
            id=model.id,
            email=Email(value=model.email),
            username=model.username,
            hashed_password=model.password,
            first_name=model.first_name,
            last_name=model.last_name,
            phone_number=PhoneNumber(value=model.phone_number) if model.phone_number else None,
            is_active=model.is_active,
            is_verified=model.is_verified,
            is_staff=model.is_staff,
            is_superuser=model.is_superuser,
            last_login=model.last_login,
            created_at=model.created_at,
            updated_at=model.updated_at,
        )
