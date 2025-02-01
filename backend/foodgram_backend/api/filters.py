"""Фильтрация."""

from django_filters import (AllValuesMultipleFilter, CharFilter, FilterSet)

from recipes.models import Ingredient, Recipe


class IngredientFilter(FilterSet):
    """Кастомный класс фильтрации ингредиентов."""

    name = CharFilter(field_name='name', lookup_expr='startswith')

    class Meta:
        model = Ingredient
        fields = ['name']


class RecipeFilter(FilterSet):
    """Фильтр для рецептов."""

    tags = AllValuesMultipleFilter(field_name='tags__slug')
    is_in_shopping_cart = CharFilter(method='filter_is_in_shopping_cart')
    is_favorited = CharFilter(method='filter_is_favorited')

    class Meta:
        model = Recipe
        fields = ('tags', 'author', 'is_in_shopping_cart', 'is_favorited')

    def filter_is_in_shopping_cart(self, queryset, name, value):
        """Фильтр для наличия рецепта в корзине."""
        if self.request.user.is_authenticated and value == '1':
            return queryset.filter(shopping_carts__user=self.request.user)
        return queryset

    def filter_is_favorited(self, queryset, name, value):
        """Фильтр для наличия рецепта в избранном."""
        if self.request.user.is_authenticated and value == '1':
            return queryset.filter(favorites__user=self.request.user)
        return queryset
