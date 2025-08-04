from rest_framework import status
from rest_framework.exceptions import AuthenticationFailed, PermissionDenied
from rest_framework_simplejwt.authentication import JWTAuthentication

from .response_handler import *


class CustomJWTAuthentication(JWTAuthentication):
    def authenticate(self, request):
        try:
            return super().authenticate(request)
        except AuthenticationFailed as e:
            return ResponseHandler.error(
                "Authentication failed", str(e), status.HTTP_401_UNAUTHORIZED
            )
        except PermissionDenied as e:
            return ResponseHandler.error(
                "Permission denied", str(e), status.HTTP_403_FORBIDDEN
            )
