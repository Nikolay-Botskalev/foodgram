"""Описание моделей."""

from django.contrib.auth.models import AbstractUser
from django.conf import settings
from django.core.validators import MinValueValidator
from django.core.exceptions import ValidationError
from django.db import models

from recipes.constants import (FORBIDDEN_USERNAME, MIN_COOKING_TIME,
                               MAX_LENGTH_EMAIL, MAX_LENGTH_INGREDIENT_NAME,
                               MAX_LENGTH_MEASUREMENT_UNIT,
                               MAX_LENGTH_RECIPE_NAME, MAX_LENGTH_TAG_NAME,
                               MAX_LENGTH_TAG_SLUG, MIN_INGREDIENT_AMOUNT)


class User(AbstractUser):
    """Расширенный класс пользователя."""

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['first_name', 'last_name', 'username']

    email = models.EmailField(
        ('email address'), unique=True, max_length=MAX_LENGTH_EMAIL)
    avatar = models.ImageField('Аватар', blank=True, null=True)

    class Meta:
        """Meta."""

        verbose_name = 'Пользователь'
        verbose_name_plural = 'Пользователи'
        ordering = ['username']

    def __str__(self):
        return self.username

    def validate(self):
        """Валидация имени пользователя."""
        if self.username in FORBIDDEN_USERNAME:
            raise ValidationError(
                {'username': ['Установите другое имя пользователя.']})


class Subscription(models.Model):
    """Модель подписок."""

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='subscriptions',
        verbose_name='Подписчик'
    )
    subscriber = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='subscribers',
        verbose_name='Автор')

    class Meta:
        """Meta."""

        verbose_name = 'Подписка'
        verbose_name_plural = 'Подписки'
        ordering = ['id']

    def __str__(self):
        return f'Подписка {self.user.username} на {self.subscriber.username}'


class Favorite(models.Model):
    """Модель для хранения избранных рецептов."""

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='favorites',
        verbose_name='Пользователь'
    )
    recipe = models.ForeignKey(
        'recipes.Recipe',
        on_delete=models.CASCADE,
        related_name='favorites',
        verbose_name='Рецепт'
    )

    class Meta:
        """Meta."""

        verbose_name = 'Избранное'
        verbose_name_plural = 'Избранное'
        ordering = ['id']

    def __str__(self):
        return f'{self.recipe.name!r} в избранном у {self.user.username}'


class ShoppingCart(models.Model):
    """Модель для списка покупок."""

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='shopping_carts',
        verbose_name='Пользователь'
    )
    recipe = models.ForeignKey(
        'recipes.Recipe',
        on_delete=models.CASCADE,
        related_name='shopping_carts',
        verbose_name='Рецепт'
    )

    class Meta:
        """Meta."""

        verbose_name = 'Список покупок'
        verbose_name_plural = 'Списки покупок'
        ordering = ['id']

    def __str__(self):
        return f'{self.recipe.name!r} в списке покупок у {self.user.username}'


class Recipe(models.Model):
    """Класс рецептов."""

    name = models.CharField(
        'Название', max_length=MAX_LENGTH_RECIPE_NAME, default='Рецепт')
    image = models.ImageField('Изображение')
    text = models.TextField('Описание')
    cooking_time = models.PositiveIntegerField(
        'Время приготовления (мин.)',
        validators=[MinValueValidator(MIN_COOKING_TIME)])
    tags = models.ManyToManyField('Tags', verbose_name='Тэг')
    ingredients = models.ManyToManyField(
        'Ingredients',
        through='RecipeIngredients',
        verbose_name='Ингредиенты'
    )
    author = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='recipes',
        verbose_name='Автор'
    )
    pub_date = models.DateTimeField('Дата добавления', auto_now_add=True)

    class Meta:
        """Meta."""

        verbose_name = 'Рецепт'
        verbose_name_plural = 'Рецепты'
        ordering = ['-pub_date']
        constraints = [
            models.UniqueConstraint(
                fields=['name', 'text', 'author'],
                name='unique_recipe'
            )
        ]

    def __str__(self):
        """Вывод названия при обращении."""
        return self.name


class Ingredients(models.Model):
    """Класс ингредиентов."""

    name = models.CharField(
        'Название ингредиента',
        unique=True,
        max_length=MAX_LENGTH_INGREDIENT_NAME)
    measurement_unit = models.CharField(
        'Единица измерения',
        max_length=MAX_LENGTH_MEASUREMENT_UNIT)

    class Meta:
        """Meta."""

        verbose_name = 'Ингредиент'
        verbose_name_plural = 'Ингредиенты'
        unique_together = ('name', 'measurement_unit')

    def __str__(self):
        """Вывод названия игридиента при обращении."""
        return self.name


class RecipeIngredients(models.Model):
    """Промежуточная таблица рецепты-ингредиенты."""

    recipe = models.ForeignKey(
        Recipe,
        on_delete=models.CASCADE,
        verbose_name='Рецепт'
    )
    ingredient = models.ForeignKey(
        Ingredients,
        on_delete=models.CASCADE,
        verbose_name='Ингредиент'
    )
    amount = models.PositiveIntegerField(
        'Количество',
        validators=[MinValueValidator(MIN_INGREDIENT_AMOUNT)]
    )

    class Meta:
        """Meta."""

        verbose_name = 'Ингредиент рецепта'
        verbose_name_plural = 'Ингредиенты рецепта'
        unique_together = ('recipe', 'ingredient')

    def __str__(self):
        return f'{self.ingredient.name} в {self.recipe.name}'


class Tags(models.Model):
    """Класс тегов."""

    name = models.CharField('Наименование', max_length=MAX_LENGTH_TAG_NAME)
    slug = models.SlugField(
        'Слаг', unique=True, max_length=MAX_LENGTH_TAG_SLUG)

    def __str__(self):
        """Вывод наименования при обращении."""
        return self.name

    class Meta:
        """Meta."""

        verbose_name = 'Тег'
        verbose_name_plural = 'Теги'
        ordering = ['name']
