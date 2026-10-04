import re

from django.core.exceptions import ValidationError


BUSINESS_CODE_PATTERN = re.compile(r'^[A-Za-z0-9](?:[A-Za-z0-9 ._/-]*[A-Za-z0-9])?$')
CONTACT_NUMBER_PATTERN = re.compile(r'^\+?[0-9 ()-]+$')


def validate_business_code_format(value):
    if not BUSINESS_CODE_PATTERN.fullmatch(value):
        raise ValidationError(
            'Use letters, numbers, spaces, periods, underscores, slashes, or hyphens.',
        )


def normalize_business_code(value):
    value = value.strip().upper()
    validate_business_code_format(value)
    return value


def validate_contact_number_format(value):
    if not value:
        return
    digits = sum(character.isdigit() for character in value)
    if not CONTACT_NUMBER_PATTERN.fullmatch(value) or not 5 <= digits <= 15:
        raise ValidationError(
            'Enter 5–15 digits; +, spaces, parentheses, and hyphens are allowed.',
        )


def normalize_contact_number(value):
    value = value.strip()
    validate_contact_number_format(value)
    return value
