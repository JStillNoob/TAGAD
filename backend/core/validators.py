from django.core.exceptions import ValidationError


class CharacterMixValidator:
    def validate(self, password, user=None):
        missing = []
        if not any(character.isupper() for character in password):
            missing.append('an uppercase letter')
        if not any(character.islower() for character in password):
            missing.append('a lowercase letter')
        if not any(character.isdigit() for character in password):
            missing.append('a number')
        if not any(not character.isalnum() for character in password):
            missing.append('a symbol')
        if missing:
            raise ValidationError(
                f"This password must contain {', '.join(missing)}.",
                code='password_missing_character_types',
            )

    def get_help_text(self):
        return 'Your password must contain uppercase, lowercase, number, and symbol characters.'
