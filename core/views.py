from rest_framework import status, generics, permissions
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.authtoken.models import Token
from django.contrib.auth import login
from django.utils import timezone
from django.conf import settings
from rest_framework_simplejwt.tokens import RefreshToken

from .models import User, PasswordResetToken
from .serializers import *
from .utils.email_verification import *
from .utils.google_oauth import *
from django.db import transaction
import logging

logger = logging.getLogger(__name__)


class RegisterView(APIView):
    serializer_class = CustomRegisterSerializer

    @transaction.atomic
    def post(self, request):
        try:
            serializer = self.serializer_class(data=request.data)
            if not serializer.is_valid():
                return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

            user = serializer.save()

            # Send verification email
            if send_verification_email_async(user):
                return Response(
                    {"detail": "User registered successfully. Verification email sent."},
                    status=status.HTTP_201_CREATED
                )
            else:
                logger.error(
                    "Verification email failed for %s. Check templates and email config.",
                    user.email
                )
                return Response(
                    {"detail": "Account created but verification email failed. Contact support."},
                    status=status.HTTP_201_CREATED
                )

        except Exception as e:
            logger.error(f"Error occurred during registration: {str(e)}", exc_info=True)
            return Response(
                {"detail": "Internal server error. Please try again later."},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class LoginView(APIView):
    serializer_class = CustomLoginSerializer
    permission_classes = [AllowAny]

    def post(self, request):
        try:
            serializer = self.serializer_class(data=request.data, context={'request': request})
            if serializer.is_valid():
                user = serializer.validated_data['user']
                login(request, user)  # Create session if needed

                # Generate JWT tokens
                refresh = RefreshToken.for_user(user)
                access = refresh.access_token

                # Handle "remember me" logic
                remember_me = serializer.validated_data.get('remember_me', False)
                if not remember_me:
                    request.session.set_expiry(0)  # Session ends when browser closes
                else:
                    request.session.set_expiry(60 * 60 * 24 * 7)  # 1 week

                return Response({
                    'refresh': str(refresh),
                    'access': str(access),
                    'email_verified': getattr(user, 'email_verified', False)
                }, status=status.HTTP_200_OK)

            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        except Exception as e:
            logger.error(f"Error occurred during signing in: {e}", exc_info=True)
            return Response(
                {"message": "Internal Server Error", "data": None},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


class VerifyEmailView(APIView):
    serializer_class = EmailVerificationSerializer

    def get(self, request):
        return Response(
            {
                "message": "Password verify email endpoint.."
            },
            status=status.HTTP_200_OK
        )

    @transaction.atomic
    def post(self, request):
        try:
            serializer = self.serializer_class(data=request.data)
            if serializer.is_valid():
                user = serializer.validated_data['user']
                user.verify_email()
                return Response(
                    {"detail": "Email verified successfully."},
                    status=status.HTTP_200_OK
                )
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            logger.error(f"Error occurred during verification: {e}")
            return Response(
                {"message": "Internal Server Error", "data": None},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


class ResendVerificationView(APIView):
    serializer_class = ResendVerificationSerializer

    @transaction.atomic
    def post(self, request):
        try:
            serializer = self.serializer_class(data=request.data)
            if serializer.is_valid():
                email = serializer.validated_data['email']
                try:
                    user = User.objects.get(email=email)
                    if send_verification_email_async(user):
                        return Response(
                            {"detail": "Verification email resent successfully."},
                            status=status.HTTP_200_OK
                        )
                    else:
                        return Response(
                            {"detail": "Failed to send verification email."},
                            status=status.HTTP_500_INTERNAL_SERVER_ERROR
                        )
                except User.DoesNotExist:
                    # Consistent with security practices - don't reveal if email exists
                    return Response(
                        {"detail": "If this email exists, a verification email has been sent."},
                        status=status.HTTP_200_OK
                    )
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            logger.error(f"Error occurred while resending verification link: {e}")
            return Response(
                {"message": "Internal Server Error", "data": None},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


class ForgotPasswordView(APIView):
    serializer_class = ForgotPasswordSerializer
    permission_classes = [AllowAny]

    @transaction.atomic
    def post(self, request):
        try:
            serializer = self.serializer_class(data=request.data)
            if serializer.is_valid():
                email = serializer.validated_data['email']

                try:
                    user = User.objects.get(email=email)
                    reset_token = PasswordResetToken.create_token(user)

                    send_password_reset_email_async(user, reset_token.token)

                except User.DoesNotExist:
                    # Don't reveal whether email exists — security best practice
                    pass

                return Response(
                    {"detail": "If this email exists, a password reset link has been sent."},
                    status=status.HTTP_200_OK
                )

            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        except Exception as e:
            logger.error(f"Error occurred: {e}", exc_info=True)
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
            status=status.HTTP_200_OK
        )

    @transaction.atomic
    def post(self, request):
        try:
            serializer = self.serializer_class(data=request.data)
            if serializer.is_valid():
                serializer.save()
                return Response(
                    {"detail": "Password reset successfully."},
                    status=status.HTTP_200_OK
                )
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            logger.error(f"Error occurred while resetting password: {e}")
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

            access_token = serializer.validated_data['access_token']

            # Validate Google token
            user_info = validate_google_token(access_token)
            if not user_info:
                return Response(
                    {"detail": "Invalid Google token."},
                    status=status.HTTP_400_BAD_REQUEST
                )

            # Find or create user
            user, created = get_or_create_google_user(user_info)

            # Login user
            login(request, user)
            token, _ = Token.objects.get_or_create(user=user)

            return Response({
                'token': token.key,
                'user_id': user.pk,
                'email': user.email,
                'first_name': user.first_name,
                'last_name': user.last_name,
                'email_verified': user.email_verified,
                'new_user': created
            }, status=status.HTTP_200_OK)
        except Exception as e:
            logger.error(f"Error occurred during google signing in: {e}")
            return Response(
                {"message": "Internal Server Error", "data": None},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


class LogoutView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        # Delete authentication token
        Token.objects.filter(user=request.user).delete()

        # Clear session
        request.session.flush()

        return Response(
            {"detail": "Successfully logged out."},
            status=status.HTTP_200_OK
        )


#
# class UserProfileView(generics.RetrieveUpdateAPIView):
#     serializer_class = UserProfileSerializer
#     permission_classes = [permissions.IsAuthenticated]
#
#     def get_object(self):
#         return self.request.user
#
#

