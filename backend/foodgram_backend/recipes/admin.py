"""Регистрация приложений в админке."""

from django.contrib import admin

from .models import Ingredients, MyUser, Recipes, Tags


@admin.register(MyUser)
class UserAdmin(admin.ModelAdmin):
    """Класс для модели пользователей."""

    list_display = ('username', 'email')
    search_fields = ('username', 'email')


@admin.register(Ingredients)
class IngredientsAdmin(admin.ModelAdmin):
    """Класс для модели ингредиентов."""

    list_display = ('name', 'measurement_unit')
    list_editable = ('measurement_unit',)
    search_fields = ('name',)


@admin.register(Recipes)
class RecipesAdmin(admin.ModelAdmin):
    """Класс для модели рецептов."""

    list_display = ('id', 'name', 'author', 'favorite_count')
    search_fields = ('author__username', 'name', 'tags__name')
    list_filter = ('tags',)

    @admin.display(description="Добавлений в избранное")
    def favorite_count(self, obj):
        """Отображение числа добавлений рецепта в избранное."""
        return obj.favorites.count()


@admin.register(Tags)
class TagsAdmin(admin.ModelAdmin):
    """Класс для модели тегов."""

    list_display = ('name', 'slug')
    search_fields = ('slug',)
    list_filter = ('name',)
