"""
Users module service layer.
"""
from datetime import datetime
from typing import Optional, List

from rest_framework_simplejwt.tokens import RefreshToken

from .models import UserModel
from .exceptions import (
    UserAlreadyExistsError,
    UserNotFoundError,
    InvalidCredentialsError,
    UserInactiveError,
)


class UserService:
    """
    User business logic service.
    """

    def get_user_by_id(self, user_id: int) -> Optional[UserModel]:
        """Get user by ID."""
        try:
            return UserModel.objects.get(id=user_id, deleted_at__isnull=True)
        except UserModel.DoesNotExist:
            return None

    def get_user_by_email(self, email: str) -> Optional[UserModel]:
        """Get user by email."""
        try:
            return UserModel.objects.get(email=email, deleted_at__isnull=True)
        except UserModel.DoesNotExist:
            return None

    def register_user(
        self,
        email: str,
        nickname: str,
        password: str,
    ) -> UserModel:
        """Register a new user."""
        if UserModel.objects.filter(email=email).exists():
            raise UserAlreadyExistsError(field="email", value=email)

        if UserModel.objects.filter(nickname=nickname).exists():
            raise UserAlreadyExistsError(field="nickname", value=nickname)

        user = UserModel.objects.create_user(
            email=email,
            nickname=nickname,
            password=password,
        )

        return user

    def authenticate(self, email: str, password: str) -> dict:
        """Authenticate user and return tokens."""
        user = self.get_user_by_email(email)

        if not user or not user.check_password(password):
            raise InvalidCredentialsError()

        if not user.is_active:
            raise UserInactiveError(str(user.id))

        refresh = RefreshToken.for_user(user)

        return {
            'access_token': str(refresh.access_token),
            'refresh_token': str(refresh),
            'token_type': 'Bearer',
            'user': user,
        }

    def update_profile(
        self,
        user_id: int,
        nickname: str = None,
    ) -> UserModel:
        """Update user profile."""
        user = self.get_user_by_id(user_id)
        if not user:
            raise UserNotFoundError(str(user_id))

        if nickname is not None:
            if UserModel.objects.filter(nickname=nickname).exclude(id=user_id).exists():
                raise UserAlreadyExistsError(field="nickname", value=nickname)
            user.nickname = nickname

        user.save()
        return user

    def update_token_balance(
        self,
        user_id: int,
        amount: int,
    ) -> UserModel:
        """Update user token balance."""
        user = self.get_user_by_id(user_id)
        if not user:
            raise UserNotFoundError(str(user_id))

        user.token_balance = (user.token_balance or 0) + amount
        user.save()
        return user

    def get_all_users(
        self,
        is_active: bool = None,
        offset: int = 0,
        limit: int = 20,
    ) -> List[UserModel]:
        """Get all users with optional filters."""
        queryset = UserModel.objects.filter(deleted_at__isnull=True)
        if is_active is not None:
            queryset = queryset.filter(is_active=is_active)
        return list(queryset.order_by('-created_at')[offset:offset + limit])

    def delete_user(self, user_id: int) -> bool:
        """Soft delete a user."""
        user = self.get_user_by_id(user_id)
        if not user:
            return False

        user.deleted_at = datetime.now()
        user.is_active = False
        user.save()
        return True
