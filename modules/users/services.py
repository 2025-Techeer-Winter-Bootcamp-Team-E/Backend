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

import requests



class UserService:
    """
    User business logic service.
    """

    def social_login(self, provider: str, social_token: str) -> dict:
        """Social login: authenticate or create user from social provider."""
        try:
            # Get user info from social provider
            social_user = SocialAuthService.get_user_info(provider, social_token)
        except (requests.RequestException, ValueError, KeyError):
            # Invalid token or unsupported provider
            raise InvalidCredentialsError()

        # Get or create user by social provider and ID
        user, created = UserModel.objects.get_or_create(
            social_provider=social_user["provider"],
            social_id=social_user["provider_id"],
            defaults={
                'email': social_user.get("email") or f"{social_user['provider']}_{social_user['provider_id']}@social.local",
                'name': social_user.get("name") or social_user["provider_id"],
                'nickname': social_user.get("name") or f"{social_user['provider']}_{social_user['provider_id']}",
                'password': UserModel.objects.make_random_password(),  # Random password for social users
                'is_active': True,
            }
        )

        # If user exists but was soft deleted, reactivate
        if user.is_deleted:
            user.deleted_at = None
            user.is_active = True
            user.save()

        if not user.is_active:
            raise UserInactiveError(str(user.id))

        # Generate JWT tokens
        refresh = RefreshToken.for_user(user)

        return {
            'access_token': str(refresh.access_token),
            'refresh_token': str(refresh),
            'token_type': 'Bearer',
            'user': user,
        }


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
        name: str,
        nickname: str,
        password: str,
        phone: str = None,
    ) -> UserModel:
        """Register a new user."""
        if UserModel.objects.filter(email=email).exists():
            raise UserAlreadyExistsError(field="email", value=email)

        if UserModel.objects.filter(nickname=nickname).exists():
            raise UserAlreadyExistsError(field="nickname", value=nickname)

        user = UserModel.objects.create_user(
            email=email,
            name=name,
            nickname=nickname,
            password=password,
            phone=phone,
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
        
    def change_password(self, user, current_password: str, new_password: str):
        # 1. 현재 비밀번호 확인
        if not user.check_password(current_password):
            raise InvalidCredentialsError("현재 비밀번호가 올바르지 않습니다.")

        # 2. 새 비밀번호 설정
        user.set_password(new_password)
        user.save()

        return True





# ⬇"외부 인증" 영역 (카카오/구글)
class SocialAuthService:

    @staticmethod
    def get_user_info(provider: str, access_token: str) -> dict:
        if provider == "kakao":
            return SocialAuthService._kakao(access_token)
        if provider == "google":
            return SocialAuthService._google(access_token)
        raise ValueError("Unsupported provider")

    @staticmethod
    def _kakao(access_token: str) -> dict:
        resp = requests.get(
            "https://kapi.kakao.com/v2/user/me",
            headers={"Authorization": f"Bearer {access_token}"}
        )
        resp.raise_for_status()
        data = resp.json()

        return {
            "provider": "kakao",
            "provider_id": str(data["id"]),
            "email": data["kakao_account"].get("email"),
            "name": data["properties"].get("nickname"),
        }

    @staticmethod
    def _google(access_token: str) -> dict:
        resp = requests.get(
            "https://www.googleapis.com/oauth2/v3/userinfo",
            headers={"Authorization": f"Bearer {access_token}"}
        )
        resp.raise_for_status()
        data = resp.json()

        return {
            "provider": "google",
            "provider_id": data["sub"],
            "email": data.get("email"),
            "name": data.get("name"),
        }


    