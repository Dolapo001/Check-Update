# core/auth_backends.py
from django.contrib.auth.backends import BaseBackend
from django.contrib.auth import get_user_model

User = get_user_model()


class EmailAuthBackend(BaseBackend):
    """
    Authenticate strictly by email + password.
    Django's `authenticate` uses the 'username' arg name, so we accept it
    but treat it as an email address.
    """
    def authenticate(self, request, username=None, password=None, **kwargs):
        email = username or kwargs.get("email")
        if not email or not password:
            return None

        try:
            user = User.objects.get(email__iexact=email)
        except User.DoesNotExist:
            return None

        if user.check_password(password) and getattr(user, "is_active", True):
            return user
        return None

    def get_user(self, user_id):
        try:
            return User.objects.get(pk=user_id)
        except User.DoesNotExist:
            return None
