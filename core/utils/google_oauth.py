import logging
from google.oauth2 import id_token
from google.auth.transport import requests
from django.conf import settings
from core.models import User

logger = logging.getLogger(__name__)


def validate_google_token(access_token):
    """
    Validate Google access token and return user info
    Returns None if validation fails
    """
    try:
        # Verify Google token
        id_info = id_token.verify_oauth2_token(
            access_token,
            requests.Request(),
            settings.GOOGLE_OAUTH2_CLIENT_ID
        )

        # Verify token audience matches our client ID
        if id_info['aud'] != settings.GOOGLE_OAUTH2_CLIENT_ID:
            logger.error("Google token audience mismatch")
            return None

        return id_info
    except ValueError as e:
        logger.error(f"Google token validation failed: {str(e)}")
        return None
    except Exception as e:
        logger.exception("Unexpected error during Google token validation")
        return None


def get_or_create_google_user(user_info):
    """
    Find or create user based on Google user info
    Returns tuple: (user, created)
    """
    email = user_info['email']
    first_name = user_info.get('given_name', '')
    last_name = user_info.get('family_name', '')
    google_id = user_info['sub']

    try:
        user = User.objects.get(email=email)
        # Update Google ID if missing
        if not user.google_id:
            user.google_id = google_id
            user.save(update_fields=['google_id'])
        return user, False
    except User.DoesNotExist:
        # Create new user with Google info
        user = User.objects.create(
            email=email,
            first_name=first_name,
            last_name=last_name,
            google_id=google_id,
            email_verified=True  # Google already verified email
        )
        return user, True