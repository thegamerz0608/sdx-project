"""
Custom ERP Exception Classes
"""


class ERPBaseException(Exception):
    """Base exception class for all ERP application errors."""

    def __init__(self, message: str, original_error: Exception | None = None):
        super().__init__(message)
        self.message = message
        self.original_error = original_error

    def __str__(self) -> str:
        if self.original_error:
            return f"{self.message} (Caused by: {self.original_error})"
        return self.message


class DatabaseConnectionError(ERPBaseException):
    """Raised when database connection fails or drops."""

    pass


class ConfigurationError(ERPBaseException):
    """Raised when environment or application configuration is invalid."""

    pass


class AuthenticationError(ERPBaseException):
    """Raised when user login or credential verification fails."""

    pass


class ValidationError(ERPBaseException):
    """Raised when input data validation fails."""

    pass


class BusinessLogicError(ERPBaseException):
    """Raised when business rules or constraints are violated."""

    pass
