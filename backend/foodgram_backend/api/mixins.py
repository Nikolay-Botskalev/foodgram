"""Миксин с валидацией."""

from rest_framework import serializers


class ValidateUsernameMixin:
    """Миксин, запрещающий пользователю создать username 'me'."""

    def validate_username(self, value):
        if value.lower() == 'me':
            raise serializers.ValidationError(
                'Используйте другой username.'
            )
        return value
