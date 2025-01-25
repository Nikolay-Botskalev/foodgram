"""Фильтрация ингредиентов."""

from django_filters import CharFilter, FilterSet
from recipes.models import Ingredients


class IngredientFilter(FilterSet):
    """Кастомный класс фильтрации ингредиентов."""

    name = CharFilter(field_name='name', lookup_expr='icontains')

    class Meta:
        model = Ingredients
        fields = ['name']
