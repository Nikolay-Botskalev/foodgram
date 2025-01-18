"""Кастомные ограничения."""

from rest_framework.permissions import BasePermission, SAFE_METHODS


class IsAuthorOrReadOnly(BasePermission):
    """
    Кастомное ограничение. Если запрос от владельца - полный доступ.
    Иначе - только безопасные методы.
    """

    def has_object_permission(self, request, view, obj):
        if request.method in SAFE_METHODS:
            return True
        return obj.author == request.user
