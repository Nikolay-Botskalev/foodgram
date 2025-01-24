"""Фильтрация ингредиентов."""

from django_filters import FilterSet, CharFilter

from recipes.models import Ingredients


class IngredientFilter(FilterSet):
    """Кастомный класс фильтрации ингредиентов."""

    name = CharFilter(field_name='name', lookup_expr='icontains')

    class Meta:
        model = Ingredients
        fields = ['name']
