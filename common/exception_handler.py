from rest_framework.views import exception_handler as drf_exception_handler
from rest_framework.exceptions import (
    AuthenticationFailed,
    NotAuthenticated,
    PermissionDenied,
    ValidationError,
    MethodNotAllowed,
    ParseError,
    NotFound,
    Throttled,
)
from .response_handler import ResponseHandler


class CustomExceptionHandler:
    """
    Class-based custom exception handler to manage all API exceptions.
    """

    @staticmethod
    def handle(exc, context):
        response = drf_exception_handler(exc, context)

        if isinstance(exc, AuthenticationFailed):
            return ResponseHandler.error(
                message="Invalid authentication credentials.", status_code=401
            )

        if isinstance(exc, NotAuthenticated):
            return ResponseHandler.error(
                message="Authentication credentials were not provided.", status_code=401
            )

        if isinstance(exc, PermissionDenied):
            return ResponseHandler.error(
                message="You do not have permission to perform this action.",
                status_code=403,
            )

        if isinstance(exc, ValidationError):
            return ResponseHandler.error(
                message="Validation error occurred.",
                errors=response.data,
                status_code=400,
            )

        if isinstance(exc, ParseError):
            return ResponseHandler.error(message="Malformed request.", status_code=400)

        if isinstance(exc, NotFound):
            return ResponseHandler.error(
                message="The requested resource was not found.", status_code=404
            )

        if isinstance(exc, MethodNotAllowed):
            return ResponseHandler.error(
                message="Method not allowed for this endpoint.", status_code=405
            )

        if isinstance(exc, Throttled):
            return ResponseHandler.error(
                message=f"Request was throttled. Try again in {exc.wait} seconds.",
                status_code=429,
            )

        if response is None:
            return ResponseHandler.error(
                message="A server error occurred.", status_code=500
            )

        message = response.data.get("detail", "An error occurred.")
        return ResponseHandler.error(
            message=message, errors=response.data, status_code=response.status_code
        )
