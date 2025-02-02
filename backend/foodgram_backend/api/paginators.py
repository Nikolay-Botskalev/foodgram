"""Пагинатор для рецептов."""

from rest_framework.pagination import PageNumberPagination
from rest_framework.response import Response


class RecipePagination(PageNumberPagination):
    """Пагинатор для рецептов."""

    page_size_query_param = 'limit'
    page_query_param = 'page'

    def get_paginated_response(self, data):
        return Response({
            'next': self.get_next_link(),
            'previous': self.get_previous_link(),
            'count': self.page.paginator.count,
            'results': data
        })
