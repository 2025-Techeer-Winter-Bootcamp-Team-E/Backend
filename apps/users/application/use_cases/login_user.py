"""
Login user use case.
"""
from dataclasses import dataclass

from django.contrib.auth.hashers import check_password
from rest_framework_simplejwt.tokens import RefreshToken

from shared.application import UseCase, UseCaseResult
from ...domain.repositories.user_repository import UserRepository
from ...domain.exceptions import InvalidCredentialsError, UserInactiveError
from ..dtos.auth_dto import LoginDTO, TokenDTO


@dataclass
class LoginUserUseCase(UseCase[LoginDTO, TokenDTO]):
    """Use case for user login."""

    user_repository: UserRepository

    def execute(self, input_dto: LoginDTO) -> UseCaseResult[TokenDTO]:
        # Find user by email
        user = self.user_repository.find_by_email(input_dto.email)

        if user is None:
            raise InvalidCredentialsError()

        # Check password
        if not check_password(input_dto.password, user.hashed_password):
            raise InvalidCredentialsError()

        # Check if user is active
        if not user.is_active:
            raise UserInactiveError(str(user.id))

        # Record login
        user.record_login()
        self.user_repository.save(user)

        # Generate tokens
        # We need to get the Django user model for JWT
        from apps.users.infrastructure.models.user_model import UserModel
        django_user = UserModel.objects.get(id=user.id)
        refresh = RefreshToken.for_user(django_user)

        return UseCaseResult.ok(
            TokenDTO(
                access_token=str(refresh.access_token),
                refresh_token=str(refresh),
                token_type="Bearer",
            )
        )
