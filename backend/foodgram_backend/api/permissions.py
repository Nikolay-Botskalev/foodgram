"""Кастомные ограничения."""

from rest_framework.permissions import SAFE_METHODS, BasePermission


class IsAuthorOrReadOnly(BasePermission):
    """
    Ограничение, представляющее доступ только автору.

    Остальным пользователям доступны только безопасные методы.

    Методы
    ------
    has_object_permission(self, request, view, obj):
        Проверяет права пользователя на выполнение запроса.
    """

    def has_object_permission(self, request, view, obj):
        """
        Проверяет, имеет ли пользователь право на выполнение запроса.

        Параметры
        ------
        request (Request): Запрос от клиента.
        view (View): Представление, обрабатывающее запрос.
        obj: Объект, к которому запрашивается доступ.

        Возвращаемое значение:
        bool: True, если запрос метод безопасный или пользователь - автор.
            False в противном случае.
        """
        return request.method in SAFE_METHODS or obj.author == request.user
