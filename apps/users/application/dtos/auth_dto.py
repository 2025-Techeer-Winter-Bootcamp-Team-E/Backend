"""
Authentication DTOs.
"""
from dataclasses import dataclass


@dataclass
class LoginDTO:
    """DTO for login request."""
    email: str
    password: str


@dataclass
class TokenDTO:
    """DTO for token response."""
    access_token: str
    refresh_token: str
    token_type: str = "Bearer"


@dataclass
class RefreshTokenDTO:
    """DTO for refresh token request."""
    refresh_token: str
