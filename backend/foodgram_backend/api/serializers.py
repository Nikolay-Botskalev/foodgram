"""Сериализаторы."""

import base64

from django.contrib.auth import password_validation
from django.core.files.base import ContentFile
from rest_framework import serializers
from rest_framework.exceptions import ValidationError

from api.mixins import ValidateUsernameMixin
from recipes.models import (
    Ingredients, RecipeIngredients, Recipes, MyUser, Tags)


class BaseUserSerializer(serializers.ModelSerializer):

    avatar = serializers.SerializerMethodField()
    is_subscribed = serializers.SerializerMethodField(default=False)

    def get_avatar(self, obj):
        return self.context['request'].build_absolute_uri(
            obj.avatar.url) if obj.avatar else None

    def get_is_subscribed(self, obj):
        user = self.context.get('request').user
        if user.is_anonymous:
            return False
        try:
            return user.is_subscribed.filter(id=obj.id).exists()
        except AttributeError:
            return False

    def get_recipes(self, obj):
        return ShortRecipeSerializer(
            obj.recipes.all(), many=True, context=self.context).data

    def get_recipes_count(self, obj):
        return obj.recipes.count()

    class Meta:
        model = MyUser
        fields = ('id', 'username', 'email', 'first_name', 'last_name',
                  'avatar', 'is_subscribed', 'password')
        read_only_fields = ('id',)
        extra_kwargs = {"email": {"required": True}}


class SetPasswordSerializer(serializers.Serializer):
    """Сериализатор для смены пароля."""

    new_password = serializers.CharField(required=True)
    current_password = serializers.CharField(required=True)


class LoginSerializer(serializers.Serializer):
    """Сериализатор для получения токена."""

    email = serializers.EmailField(required=True)
    password = serializers.CharField(required=True)


class UserSerializer(ValidateUsernameMixin, BaseUserSerializer):
    """Позволяет пользователю взаимодействовать со своими данными."""

    password = serializers.CharField(
        write_only=True,
        required=True,
        validators=[password_validation.validate_password],
    )
    email = serializers.EmailField(required=True)

    def create(self, validated_data):
        """Метод для создания нового пользователя."""
        user = MyUser.objects.create(**validated_data)
        return user


class SubscribedUserSerializer(UserSerializer):
    """Сериализатор для вывода информации о подписках."""

    recipes = serializers.SerializerMethodField()
    recipes_count = serializers.SerializerMethodField()

    class Meta:
        """Meta."""

        model = MyUser
        fields = ('id', 'username', 'email', 'first_name', 'last_name',
                  'avatar', 'is_subscribed', 'recipes', 'recipes_count')


class Base64Image(serializers.ImageField):
    """Кастомный тип поля картинки."""

    def to_internal_value(self, data):
        if not data:
            return None
        if isinstance(data, str) and data.startswith('data:image'):
            format, imgstr = data.split(';base64,')
            ext = format.split('/')[-1]
            if not ext:
                raise serializers.ValidationError(
                    'Неправильный формат изображения')
            data = ContentFile(base64.b64decode(imgstr), name='temp.' + ext)
        return super().to_internal_value(data)


class AvatarSerializer(serializers.ModelSerializer):
    """Сериализатор для аватара."""

    avatar = Base64Image(required=True, allow_null=False)

    class Meta:
        """Meta."""

        model = MyUser
        fields = ('avatar',)


class IngredientsSerializer(serializers.ModelSerializer):
    """Сериализатор рецептов."""

    class Meta:
        """Meta."""

        model = Ingredients
        fields = ('id', 'name', 'measurement_unit')


class ShortRecipeSerializer(serializers.ModelSerializer):
    """Сериализатор для вывода рецептов в подписках."""

    image = Base64Image(required=False, allow_null=True)

    class Meta:
        """Meta."""

        model = Recipes
        fields = ('id', 'name', 'image', 'cooking_time')


class RecipeIngredientSerializer(serializers.ModelSerializer):
    """Сериализатор вспомогательной модели рецепты-ингредиенты."""

    id = serializers.CharField(source='ingredient.id', read_only=True)
    name = serializers.CharField(source='ingredient.name', read_only=True)
    measurement_unit = serializers.CharField(
        source='ingredient.measurement_unit', read_only=True)
    amount = serializers.DecimalField(
        max_digits=6, decimal_places=2, required=True)

    class Meta:
        """Meta."""

        model = RecipeIngredients
        fields = ('id', 'name', 'measurement_unit', 'amount')


class TagsSerializer(serializers.ModelSerializer):
    """Сериализатор рецептов."""

    name = serializers.ReadOnlyField()
    slug = serializers.ReadOnlyField()

    class Meta:
        """Meta."""

        model = Tags
        fields = ('id', 'name', 'slug')


class RecipeSerializer(serializers.ModelSerializer):
    """Общий сериализатор для рецептов."""

    image = Base64Image(required=True)
    author = UserSerializer(
        read_only=True, default=serializers.CurrentUserDefault())
    is_favorited = serializers.SerializerMethodField(default=False)
    is_in_shopping_cart = serializers.SerializerMethodField(default=False)
    tags = TagsSerializer(many=True, read_only=True)
    ingredients = serializers.SerializerMethodField()

    class Meta:
        """Meta."""

        model = Recipes
        fields = (
            'id', 'author', 'name', 'image', 'text', 'ingredients',
            'tags', 'cooking_time', 'is_favorited', 'is_in_shopping_cart',
        )
        read_only_fields = (
            'id', 'is_favorited', 'is_in_shopping_cart', 'author')

    def get_is_favorited(self, obj):
        user = self.context.get('request').user
        if user.is_authenticated:
            return user.favorites.filter(id=obj.id).exists()
        return False

    def get_is_in_shopping_cart(self, obj):
        user = self.context.get('request').user
        if user.is_authenticated:
            return user.shopping_cart.filter(id=obj.id).exists()
        return False

    def get_ingredients(self, obj):
        recipe_ingredients = obj.recipeingredients_set.all()
        return [RecipeIngredientSerializer(
            item).data for item in recipe_ingredients]

    def to_internal_value(self, data):
        tags = data.get('tags')
        ingredients = data.get('ingredients')
        internal_data = super().to_internal_value(data)
        if tags:
            for tag_id in tags:
                try:
                    Tags.objects.get(pk=tag_id)
                except Tags.DoesNotExist:
                    raise ValidationError(
                        {'classes': ['Тег отсутствует.']},
                        code='invalid',
                    )
        internal_data['tags'] = tags
        internal_data['ingredients'] = ingredients
        return internal_data

    def create(self, validated_data):
        """Создание рецепта."""
        tags_data = validated_data.pop('tags')
        ingredients_data = validated_data.pop('ingredients')
        recipe = Recipes.objects.create(**validated_data)
        recipe.tags.set(tags_data)
        for ingredient_data in ingredients_data:
            ingredient_obj = Ingredients.objects.get(
                id=ingredient_data['id']
            )
            RecipeIngredients.objects.create(
                recipe=recipe,
                ingredient=ingredient_obj,
                amount=ingredient_data['amount']
            )
        return recipe

    def update(self, instance, validated_data):
        """Обновление рецепта."""
        tags_data = validated_data.pop('tags', None)
        ingredients_data = validated_data.pop('ingredients', None)

        if tags_data is not None:
            instance.tags.set(tags_data)

        if ingredients_data is not None:
            instance.recipeingredients_set.all().delete()
            for ingredient_data in ingredients_data:
                ingredient_obj = Ingredients.objects.get(
                    id=ingredient_data['id']
                )
                RecipeIngredients.objects.create(
                    recipe=instance,
                    ingredient=ingredient_obj,
                    amount=ingredient_data['amount']
                )
        for key, value in validated_data.items():
            setattr(instance, key, value)
        instance.save()
        return instance
