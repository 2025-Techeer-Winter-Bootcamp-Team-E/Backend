"""
Base use case classes.
"""
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Generic, TypeVar, Optional, Any

InputDTO = TypeVar('InputDTO')
OutputDTO = TypeVar('OutputDTO')


@dataclass
class UseCaseResult(Generic[OutputDTO]):
    """Result wrapper for use cases."""
    success: bool
    data: Optional[OutputDTO] = None
    error: Optional[str] = None
    error_code: Optional[str] = None

    @classmethod
    def ok(cls, data: OutputDTO) -> 'UseCaseResult[OutputDTO]':
        """Create a successful result."""
        return cls(success=True, data=data)

    @classmethod
    def fail(cls, error: str, error_code: str = None) -> 'UseCaseResult[OutputDTO]':
        """Create a failed result."""
        return cls(success=False, error=error, error_code=error_code)


class UseCase(ABC, Generic[InputDTO, OutputDTO]):
    """Base use case class."""

    @abstractmethod
    def execute(self, input_dto: InputDTO) -> UseCaseResult[OutputDTO]:
        """Execute the use case."""
        pass


class AsyncUseCase(ABC, Generic[InputDTO, OutputDTO]):
    """Base async use case class."""

    @abstractmethod
    async def execute(self, input_dto: InputDTO) -> UseCaseResult[OutputDTO]:
        """Execute the use case asynchronously."""
        pass
