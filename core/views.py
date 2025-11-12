# views.py
import logging
import time
from time import sleep

from django.conf import settings
from django.db import transaction
from django.contrib.auth import login
from rest_framework import status
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.authtoken.models import Token
from rest_framework_simplejwt.tokens import RefreshToken

from .models import User, PasswordResetToken
from .serializers import (
    CustomRegisterSerializer,
    CustomLoginSerializer,
    EmailVerificationSerializer,
    ResendVerificationSerializer,
    ForgotPasswordSerializer,
    ResetPasswordSerializer,
    GoogleOAuthSerializer,
)
from .utils.google_oauth import validate_google_token, get_or_create_google_user
from core.utils.email_verification import (
    send_verification_email_sync,
    send_password_reset_email_sync,
)

logger = logging.getLogger(__name__)

# Configurable retry behavior (tunable via settings)
EMAIL_SEND_RETRY_COUNT = int(
    getattr(settings, "EMAIL_SEND_RETRY_COUNT", 1)
)  # total attempts
EMAIL_SEND_RETRY_BACKOFF = float(
    getattr(settings, "EMAIL_SEND_RETRY_BACKOFF", 0.5)
)  # seconds between attempts


class EmailSendError(Exception):
    """Raised when email sending fails after retries."""


def _attempt_send(send_fn, *args, **kwargs) -> bool:
    """
    Attempt to call send_fn(*args, **kwargs) synchronously with a small retry loop.
    Returns True on success, False on failure.
    Minimal blocking to avoid long delays.
    """
    last_exc = None
    attempts = max(1, EMAIL_SEND_RETRY_COUNT)
    backoff = float(EMAIL_SEND_RETRY_BACKOFF)

    for attempt in range(1, attempts + 1):
        try:
            success = send_fn(*args, **kwargs)
            if success:
                return True
            # success == False counts as a failure we may retry
            last_exc = None
        except Exception as exc:
            last_exc = exc
            logger.exception(
                "Exception during email send (attempt %d/%d): %s",
                attempt,
                attempts,
                exc,
            )

        # If not last attempt, wait a small backoff
        if attempt < attempts:
            try:
                sleep(backoff)
            except Exception:
                # If sleep is interrupted just continue
                pass
            # exponential-ish backoff for subsequent retries
            backoff *= 2

    # After exhausting attempts
    if last_exc:
        logger.error("Email send failed after %d attempts: %s", attempts, last_exc)
    else:
        logger.error("Email send returned False after %d attempts.", attempts)
    return False


class RegisterView(APIView):
    serializer_class = CustomRegisterSerializer

    @transaction.atomic
    def post(self, request):
        """
        Create user and send verification email synchronously.
        If email sending fails, rollback user creation and return 502.
        """
        try:
            serializer = self.serializer_class(data=request.data)
            if not serializer.is_valid():
                return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

            user = serializer.save()

            # Attempt to send verification email synchronously (with minimal retries)
            sent = _attempt_send(send_verification_email_sync, user, False)

            if not sent:
                # Rollback user creation and inform the client
                logger.error(
                    "Verification email failed for %s; rolling back user creation.",
                    user.email,
                )
                # Raising an exception inside atomic will rollback
                raise EmailSendError(
                    "Failed to send verification email. Please try again later."
                )

            logger.info("User registered and verification email sent to %s", user.email)
            return Response(
                {"detail": "User registered successfully. Verification email sent."},
                status=status.HTTP_201_CREATED,
            )

        except EmailSendError as ese:
            # This will rollback the transaction because we are inside @transaction.atomic
            logger.exception("EmailSendError during registration: %s", ese)
            return Response(
                {
                    "detail": "Failed to send verification email. Please try again later."
                },
                status=status.HTTP_502_BAD_GATEWAY,
            )
        except Exception as e:
            logger.exception("Error occurred during registration: %s", e)
            return Response(
                {"detail": "Internal server error. Please try again later."},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


class LoginView(APIView):
    serializer_class = CustomLoginSerializer
    permission_classes = [AllowAny]

    def post(self, request):
        try:
            serializer = self.serializer_class(
                data=request.data, context={"request": request}
            )
            if serializer.is_valid():
                user = serializer.validated_data["user"]
                login(request, user)

                refresh = RefreshToken.for_user(user)
                access = refresh.access_token

                remember_me = serializer.validated_data.get("remember_me", False)
                if not remember_me:
                    request.session.set_expiry(0)
                else:
                    request.session.set_expiry(60 * 60 * 24 * 7)  # 1 week

                return Response(
                    {
                        "refresh": str(refresh),
                        "access": str(access),
                        "email_verified": getattr(user, "email_verified", False),
                    },
                    status=status.HTTP_200_OK,
                )

            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        except Exception as e:
            logger.exception("Error occurred during signing in: %s", e)
            return Response(
                {"message": "Internal Server Error", "data": None},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


class VerifyEmailView(APIView):
    serializer_class = EmailVerificationSerializer

    def get(self, request):
        return Response(
            {"message": "Password verify email endpoint.."}, status=status.HTTP_200_OK
        )

    @transaction.atomic
    def post(self, request):
        try:
            serializer = self.serializer_class(data=request.data)
            if serializer.is_valid():
                user = serializer.validated_data["user"]
                user.verify_email()
                return Response(
                    {"detail": "Email verified successfully."},
                    status=status.HTTP_200_OK,
                )
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            logger.exception("Error occurred during verification: %s", e)
            return Response(
                {"message": "Internal Server Error", "data": None},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


class ResendVerificationView(APIView):
    serializer_class = ResendVerificationSerializer

    @transaction.atomic
    def post(self, request):
        """
        Attempt to resend verification email synchronously if the user exists.
        To avoid email enumeration, the response is always the same regardless of existence.
        """
        try:
            serializer = self.serializer_class(data=request.data)
            if serializer.is_valid():
                email = serializer.validated_data["email"]
                try:
                    user = User.objects.get(email=email)
                    sent = _attempt_send(send_verification_email_sync, user, True)
                    if sent:
                        logger.info("Verification email resent to %s", email)
                    else:
                        # Log failure but do not reveal to client
                        logger.error("Failed to resend verification email to %s", email)
                except User.DoesNotExist:
                    logger.info(
                        "Resend verification requested for non-existing email: %s",
                        email,
                    )
                    # intentionally do nothing - keep response ambiguous

                return Response(
                    {
                        "detail": "If this email exists, a verification email has been sent."
                    },
                    status=status.HTTP_200_OK,
                )
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        except Exception as e:
            logger.exception("Error occurred while resending verification link: %s", e)
            return Response(
                {"message": "Internal Server Error", "data": None},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


class ForgotPasswordView(APIView):
    serializer_class = ForgotPasswordSerializer
    permission_classes = [AllowAny]

    @transaction.atomic
    def post(self, request):
        """
        Attempt to create a reset token and send email synchronously if user exists.
        Response is intentionally ambiguous to avoid enumeration.
        """
        try:
            serializer = self.serializer_class(data=request.data)
            if serializer.is_valid():
                email = serializer.validated_data["email"]

                try:
                    user = User.objects.get(email=email)
                    reset_token = PasswordResetToken.create_token(user)

                    sent = _attempt_send(
                        send_password_reset_email_sync, user, reset_token.token, True
                    )
                    if sent:
                        logger.info("Password reset email sent to %s", email)
                    else:
                        logger.error("Failed to send password reset email to %s", email)
                except User.DoesNotExist:
                    logger.info(
                        "ForgotPassword requested for non-existing email: %s", email
                    )
                    # keep response ambiguous

                return Response(
                    {
                        "detail": "If this email exists, a password reset link has been sent."
                    },
                    status=status.HTTP_200_OK,
                )

            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        except Exception as e:
            logger.exception("Error occurred in ForgotPasswordView: %s", e)
            return Response(
                {"message": "Internal Server Error", "data": None},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


class ResetPasswordView(APIView):
    serializer_class = ResetPasswordSerializer

    def get(self, request):
        return Response(
            {
                "message": "Password reset endpoint. Submit a POST request with token and new password."
            },
            status=status.HTTP_200_OK,
        )

    @transaction.atomic
    def post(self, request):
        try:
            serializer = self.serializer_class(data=request.data)
            if serializer.is_valid():
                serializer.save()
                return Response(
                    {"detail": "Password reset successfully."},
                    status=status.HTTP_200_OK,
                )
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            logger.exception("Error occurred while resetting password: %s", e)
            return Response(
                {"message": "Internal Server Error", "data": None},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


class GoogleOAuthView(APIView):
    serializer_class = GoogleOAuthSerializer

    @transaction.atomic
    def post(self, request):
        try:
            serializer = self.serializer_class(data=request.data)
            if not serializer.is_valid():
                return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

            access_token = serializer.validated_data["access_token"]
            user_info = validate_google_token(access_token)
            if not user_info:
                return Response(
                    {"detail": "Invalid Google token."},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            user, created = get_or_create_google_user(user_info)
            login(request, user)
            token, _ = Token.objects.get_or_create(user=user)

            return Response(
                {
                    "token": token.key,
                    "user_id": user.pk,
                    "email": user.email,
                    "first_name": user.first_name,
                    "last_name": user.last_name,
                    "email_verified": user.email_verified,
                    "new_user": created,
                },
                status=status.HTTP_200_OK,
            )

        except Exception as e:
            logger.exception("Error occurred during google signing in: %s", e)
            return Response(
                {"message": "Internal Server Error", "data": None},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


class LogoutView(APIView):
    permission_classes = []

    def post(self, request):
        Token.objects.filter(user=request.user).delete()
        request.session.flush()
        return Response(
            {"detail": "Successfully logged out."}, status=status.HTTP_200_OK
        )
