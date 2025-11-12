from django.http import JsonResponse
from django.utils.deprecation import MiddlewareMixin
from rest_framework import status


class BlacklistMiddleware(MiddlewareMixin):
    def process_request(self, request):  # noqa
        # Move the imports here instead
        from rest_framework_simplejwt.tokens import AccessToken
        from .models import BlacklistedToken

        # Check if the token is in the blacklist
        token = request.headers.get("Authorization", None)
        try:
            if token:
                # Extract the token part
                token = token.split(" ")[1]
                access_token = AccessToken(token)
                jti = access_token["jti"]

                # Check if the token's jti is in the blacklist
                if BlacklistedToken.objects.filter(jti=jti).exists():
                    return JsonResponse(
                        {
                            "status": "error",
                            "message": "This access token has been revoked.",
                            "errors": "Revoked access token",
                        },
                        status=status.HTTP_401_UNAUTHORIZED,
                    )

        except Exception as e:  # noqa
            return JsonResponse(
                {
                    "status": "error",
                    "message": "This token is either invalid or expired.",
                    "errors": "Expired/invalid access token",
                },
                status=status.HTTP_401_UNAUTHORIZED,
            )
