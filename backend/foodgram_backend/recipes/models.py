"""Описание моделей."""

from django.contrib.auth.models import AbstractUser
from django.core.validators import MinValueValidator
from django.db import models


class MyUser(AbstractUser):
    """Расширенный класс пользователя."""

    is_subscribed = models.ManyToManyField(
        'self',
        symmetrical=False,
        blank=True,
        related_name='followers'
    )
    favorites = models.ManyToManyField(
        'recipes.Recipes',
        related_name='favorites',
        verbose_name='Избранное',
        blank=True
    )
    shopping_cart = models.ManyToManyField(
        'recipes.Recipes',
        related_name='shopping_cart',
        verbose_name='Корзина',
        blank=True
    )
    email = models.EmailField(('email address'), unique=True, max_length=100)
    avatar = models.ImageField('Аватар', blank=True, null=True)

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['username']

    class Meta:
        """Meta."""

        verbose_name = 'Пользователь'
        verbose_name_plural = 'Пользователи'


class Recipes(models.Model):
    """Класс рецептов."""

    name = models.CharField('Название', max_length=256, default='Рецепт')
    image = models.ImageField('Изображение', blank=True, null=True)
    text = models.TextField('Описание', blank=True)
    cooking_time = models.PositiveIntegerField(
        'Время приготовления (мин.)', validators=[MinValueValidator(1)])
    tags = models.ManyToManyField('Tags', verbose_name='Тэг')
    ingredients = models.ManyToManyField(
        'Ingredients',
        through='RecipeIngredients',
        verbose_name='Ингредиенты'
    )
    author = models.ForeignKey(
        MyUser,
        on_delete=models.CASCADE,
        related_name='recipes',
        verbose_name='Автор'
    )
    pub_date = models.DateTimeField('Дата добавления', auto_now_add=True)

    def __str__(self):
        """Вывод названия при обращении."""
        return self.name

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


class Ingredients(models.Model):
    """Класс ингредиентов."""

    name = models.CharField('Название ингредиента', max_length=50, unique=True)
    measurement_unit = models.CharField('Единица измерения', max_length=15)

    def __str__(self):
        """Вывод названия игридиента при обращении."""
        return self.name

    class Meta:
        """Meta."""

        verbose_name = 'Ингредиент'
        verbose_name_plural = 'Ингредиенты'


class RecipeIngredients(models.Model):
    """Промежуточная таблица рецепты-ингредиенты."""

    recipe = models.ForeignKey(
        Recipes,
        on_delete=models.CASCADE,
        verbose_name='Рецепт'
    )
    ingredient = models.ForeignKey(
        Ingredients,
        on_delete=models.CASCADE,
        verbose_name='Ингредиент'
    )
    amount = models.DecimalField(
        'Количество',
        max_digits=500,
        decimal_places=2,
        validators=[MinValueValidator(0.01)]
    )

    class Meta:
        """Meta."""

        verbose_name = 'Ингредиент рецепта'
        verbose_name_plural = 'Ингредиенты рецепта'


class Tags(models.Model):
    """Класс тегов."""

    name = models.CharField('Наименование', max_length=128)
    slug = models.SlugField('Слаг', max_length=128, unique=True)

    def __str__(self):
        """Вывод наименования при обращении."""
        return self.name

    class Meta:
        """Meta."""

        verbose_name = 'Тег'
        verbose_name_plural = 'Теги'
