"""Фильтрация ингредиентов."""

from django_filters import CharFilter, FilterSet
from recipes.models import Ingredients


class IngredientFilter(FilterSet):
    """Кастомный класс фильтрации ингредиентов."""

    name = CharFilter(field_name='name', lookup_expr='startswith')

    class Meta:
        model = Ingredients
        fields = ['name']
