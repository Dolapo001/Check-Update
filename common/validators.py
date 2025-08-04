from django.core.exceptions import ValidationError
from django.core.validators import validate_email
from rest_framework import serializers
from django.utils.translation import gettext_lazy as _


def validate_email_format(value):
    try:
        validate_email(value)
    except ValidationError:
        raise ValidationError("Invalid email format")


def validate_phone_number(value):
    if not value.startswith("+"):
        raise ValidationError("Phone number must start with a plus sign (+)")

    if not value[1:].isdigit():
        raise ValidationError(
            "Phone number must only contain digits after the plus sign (+)"
        )

    if len(value) < 10 or len(value) > 15:
        raise ValidationError(
            "Phone number must be between 10 and 15 digits long (excluding the plus sign)."
        )


def validate_passwords_match(data):
    if data["new_password"] != data["confirm_password"]:
        raise serializers.ValidationError("The two password fields must match.")
    return data
