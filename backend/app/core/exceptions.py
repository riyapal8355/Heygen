"""Centralized domain and API exception classes."""

from typing import Any, Optional
from fastapi import status


class AppException(Exception):
    """Base application exception supporting structured machine-readable error codes."""

    def __init__(
        self,
        status_code: int = status.HTTP_400_BAD_REQUEST,
        code: str = "BAD_REQUEST",
        message: str = "An error occurred.",
        details: Optional[Any] = None,
        retryable: bool = False,
    ):
        self.status_code = status_code
        self.code = code
        self.message = message
        self.details = details
        self.retryable = retryable
        super().__init__(message)


class AuthenticationException(AppException):
    def __init__(self, message: str = "Authentication failed.", code: str = "AUTH_INVALID_CREDENTIALS"):
        super().__init__(
            status_code=status.HTTP_401_UNAUTHORIZED,
            code=code,
            message=message,
        )


class ForbiddenException(AppException):
    def __init__(self, message: str = "You do not have permission to perform this action.", code: str = "FORBIDDEN"):
        super().__init__(
            status_code=status.HTTP_403_FORBIDDEN,
            code=code,
            message=message,
        )


class NotFoundException(AppException):
    def __init__(
        self,
        message: str = "The requested resource was not found.",
        code: str = "NOT_FOUND",
        details: Optional[Any] = None,
    ):
        super().__init__(
            status_code=status.HTTP_404_NOT_FOUND,
            code=code,
            message=message,
            details=details,
        )


class ConflictException(AppException):
    def __init__(self, message: str = "The requested resource already exists.", code: str = "CONFLICT"):
        super().__init__(
            status_code=status.HTTP_409_CONFLICT,
            code=code,
            message=message,
        )


class RateLimitedException(AppException):
    def __init__(self, message: str = "Too many requests. Please try again later.", code: str = "RATE_LIMITED"):
        super().__init__(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            code=code,
            message=message,
        )


class AIProviderException(AppException):
    """Base exception for AI provider errors."""

    def __init__(
        self,
        message: str = "An error occurred in the AI provider.",
        code: str = "AI_PROVIDER_ERROR",
        status_code: int = status.HTTP_500_INTERNAL_SERVER_ERROR,
        details: Optional[Any] = None,
    ):
        super().__init__(
            status_code=status_code,
            code=code,
            message=message,
            details=details,
        )


class AIProviderNotFoundException(AIProviderException):
    """Raised when an AI provider for a requested capability is not registered or found."""

    def __init__(
        self,
        message: str = "Requested AI provider was not found.",
        code: str = "AI_PROVIDER_NOT_FOUND",
        details: Optional[Any] = None,
    ):
        super().__init__(
            status_code=status.HTTP_404_NOT_FOUND,
            code=code,
            message=message,
            details=details,
        )


class AIProviderValidationError(AIProviderException):
    """Raised when an AI provider does not satisfy the required capability protocol."""

    def __init__(
        self,
        message: str = "Provider does not implement the required interface protocol.",
        code: str = "AI_PROVIDER_INVALID",
        details: Optional[Any] = None,
    ):
        super().__init__(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            code=code,
            message=message,
            details=details,
        )


class AIRuntimeUnavailableException(AIProviderException):
    """Raised when an AI runtime or required compute device (e.g. CUDA GPU) is unavailable."""

    def __init__(
        self,
        message: str = "The requested AI runtime or compute accelerator is currently unavailable.",
        code: str = "AI_RUNTIME_UNAVAILABLE",
        details: Optional[Any] = None,
    ):
        super().__init__(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            code=code,
            message=message,
            details=details,
        )


class AIInferenceException(AIProviderException):
    """Raised when local AI neural inference encounters an unrecoverable failure."""

    def __init__(
        self,
        message: str = "AI inference execution failed.",
        code: str = "AI_INFERENCE_FAILED",
        details: Optional[Any] = None,
    ):
        super().__init__(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            code=code,
            message=message,
            details=details,
        )


class AIModelIncompatibleException(AIProviderException):
    """Raised when an AI model cannot be loaded or executed on the target hardware/runtime."""

    def __init__(
        self,
        message: str = "The selected model is incompatible with the target runtime or device.",
        code: str = "AI_MODEL_INCOMPATIBLE",
        details: Optional[Any] = None,
    ):
        super().__init__(
            status_code=status.HTTP_400_BAD_REQUEST,
            code=code,
            message=message,
            details=details,
        )


class AIResourceExhaustedException(AIProviderException):
    """Raised when host hardware lacks sufficient memory (RAM/VRAM) to load or execute model."""

    def __init__(
        self,
        message: str = "Insufficient hardware memory to load or execute the requested AI model.",
        code: str = "AI_INSUFFICIENT_MEMORY",
        details: Optional[Any] = None,
    ):
        super().__init__(
            status_code=status.HTTP_507_INSUFFICIENT_STORAGE,
            code=code,
            message=message,
            details=details,
        )


class AIModelSecurityException(AIProviderException):
    """Raised when model loading or caching violates security policies (traversal, hash mismatch, etc.)."""

    def __init__(
        self,
        message: str = "Model artifact failed security validation.",
        code: str = "AI_MODEL_SECURITY_VIOLATION",
        details: Optional[Any] = None,
    ):
        super().__init__(
            status_code=status.HTTP_403_FORBIDDEN,
            code=code,
            message=message,
            details=details,
        )


class ValidationException(AppException):
    """Raised when request payload or media validation fails."""

    def __init__(
        self,
        message: str = "The request payload failed validation.",
        code: str = "VALIDATION_ERROR",
        details: Optional[Any] = None,
    ):
        super().__init__(
            status_code=status.HTTP_400_BAD_REQUEST,
            code=code,
            message=message,
            details=details,
        )


class RateLimitExceededException(AppException):
    """Raised when request rate limit is exceeded."""

    def __init__(
        self,
        message: str = "Rate limit exceeded. Please try again later.",
        code: str = "RATE_LIMIT_EXCEEDED",
        retry_after: int = 60,
        details: Optional[Any] = None,
    ):
        self.retry_after = retry_after
        super().__init__(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            code=code,
            message=message,
            details=details or {"retry_after_seconds": retry_after},
            retryable=True,
        )



