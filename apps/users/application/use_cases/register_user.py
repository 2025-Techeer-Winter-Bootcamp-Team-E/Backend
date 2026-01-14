"""
Register user use case.
"""
from dataclasses import dataclass
from typing import Optional

from django.contrib.auth.hashers import make_password

from shared.application import UseCase, UseCaseResult
from ...domain.entities.user import User
from ...domain.repositories.user_repository import UserRepository
from ...domain.exceptions import UserAlreadyExistsError
from ..dtos.user_dto import UserCreateDTO, UserDTO


@dataclass
class RegisterUserUseCase(UseCase[UserCreateDTO, UserDTO]):
    """Use case for registering a new user."""

    user_repository: UserRepository

    def execute(self, input_dto: UserCreateDTO) -> UseCaseResult[UserDTO]:
        # Check if email already exists
        if self.user_repository.exists_by_email(input_dto.email):
            raise UserAlreadyExistsError(field="email", value=input_dto.email)

        # Check if username already exists
        if self.user_repository.exists_by_username(input_dto.username):
            raise UserAlreadyExistsError(field="username", value=input_dto.username)

        # Hash the password
        hashed_password = make_password(input_dto.password)

        # Create user entity
        user = User.create(
            email=input_dto.email,
            username=input_dto.username,
            hashed_password=hashed_password,
            first_name=input_dto.first_name or "",
            last_name=input_dto.last_name or "",
            phone_number=input_dto.phone_number,
        )

        # Save user
        saved_user = self.user_repository.save(user)

        # Return DTO
        return UseCaseResult.ok(UserDTO.from_entity(saved_user))
