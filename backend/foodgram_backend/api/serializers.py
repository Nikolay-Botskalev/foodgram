"""Сериализаторы."""

from django.contrib.auth import password_validation
from django.core.validators import MinValueValidator
from drf_extra_fields.fields import Base64ImageField
from rest_framework import serializers
from rest_framework.exceptions import ValidationError

from api.constants import FORBIDDEN_USERNAME, MIN_INGREDIENT_AMOUNT
from recipes.models import (
    Favorite, Ingredients, ShoppingCart, RecipeIngredients, Recipe, Tags, User)


class BaseUserSerializer(serializers.ModelSerializer):

    avatar = serializers.SerializerMethodField()
    is_subscribed = serializers.SerializerMethodField()
    password = serializers.CharField(
        write_only=True,
        required=True,
        validators=[password_validation.validate_password],
    )
    email = serializers.EmailField(required=True)

    def get_avatar(self, obj):
        return self.context['request'].build_absolute_uri(
            obj.avatar.url) if obj.avatar else None

    def get_is_subscribed(self, obj):
        user = self.context.get('request').user
        if user.is_authenticated and hasattr(user, 'is_subscribed'):
            return user.is_subscribed.filter(id=obj.id).exists()
        return False

    class Meta:
        """Meta."""

        model = User
        fields = ('id', 'username', 'email', 'first_name', 'last_name',
                  'avatar', 'is_subscribed', 'password')


class UserCreateSerializer(BaseUserSerializer):
    """Сериализатор для создания пользователя."""

    class Meta:
        """Meta."""

        model = User
        fields = ['email', 'username', 'first_name', 'last_name', 'password']
        extra_kwargs = {
            'email': {'required': True, 'allow_blank': False},
            'username': {'required': True, 'allow_blank': False},
            'first_name': {'required': True},
            'last_name': {'required': True}
        }

    def validate(self, data):
        """Валидация введенных значений"""
        if User.objects.filter(email=data.get('email')).exists():
            raise ValidationError(
                "Пользователь с таким email уже существует")
        if data.get('username') in FORBIDDEN_USERNAME:
            raise serializers.ValidationError(
                f"Имя пользователя {data.get('username')} не разрешено.")
        if User.objects.filter(username=data.get('username')).exists():
            raise ValidationError(
                "Пользователь с таким username уже существует")
        return data


class UserRegistrationSerializer(serializers.ModelSerializer):
    """Сериализатор для вывода json ответа после регистрации."""

    class Meta:
        """Meta."""

        model = User
        fields = ['email', 'id', 'username', 'first_name', 'last_name']


class SetPasswordSerializer(serializers.Serializer):
    """Сериализатор для смены пароля."""

    new_password = serializers.CharField(required=True)
    current_password = serializers.CharField(required=True)


class LoginSerializer(serializers.Serializer):
    """Сериализатор для получения токена."""

    email = serializers.EmailField(required=True)
    password = serializers.CharField(required=True)


class SubscribedUserSerializer(BaseUserSerializer):
    """Сериализатор для вывода информации о подписках."""

    recipes = serializers.SerializerMethodField()
    recipes_count = serializers.SerializerMethodField()

    class Meta:
        """Meta."""

        model = User
        fields = BaseUserSerializer.Meta.fields + ('recipes', 'recipes_count')

    def get_recipes(self, obj):
        recipes_limit = self.context.get('recipes_limit')
        recipes = obj.recipes.all()
        try:
            recipes_limit = int(
                recipes_limit) if recipes_limit is not None else None
        except (ValueError, TypeError):
            recipes_limit = None

        if recipes_limit:
            recipes = recipes[:recipes_limit]
        return ShortRecipeSerializer(
            recipes, many=True, context=self.context
        ).data

    def get_recipes_count(self, obj):
        return obj.recipes.count()


class SubscriptionSerializer(serializers.Serializer):
    """Сериализатор для подписок."""

    subscriber = serializers.PrimaryKeyRelatedField(
        queryset=User.objects.all())

    def validate(self, data):
        if self.context['request'].user == data['subscriber']:
            raise ValidationError('Нельзя подписаться на себя')
        return data

    def to_representation(self, instance):
        request = self.context.get('request')
        recipes_limit = self.context.get('recipes_limit')
        return SubscribedUserSerializer(
            instance, context={
                'request': request, 'recipes_limit': recipes_limit}).data


class AvatarSerializer(serializers.ModelSerializer):
    """Сериализатор для аватара."""

    avatar = Base64ImageField(required=True, allow_null=False)

    class Meta:
        """Meta."""

        model = User
        fields = ('avatar',)


class IngredientsSerializer(serializers.ModelSerializer):
    """Сериализатор рецептов."""

    class Meta:
        """Meta."""

        model = Ingredients
        fields = ('id', 'name', 'measurement_unit')


class ShortRecipeSerializer(serializers.ModelSerializer):
    """Сериализатор для вывода рецептов в подписках."""

    image = Base64ImageField(required=False, allow_null=True)

    class Meta:
        """Meta."""

        model = Recipe
        fields = ('id', 'name', 'image', 'cooking_time')


class RecipeIngredientSerializer(serializers.ModelSerializer):
    """Сериализатор вспомогательной модели рецепты-ингредиенты."""
    id = serializers.IntegerField(source='ingredient.id', read_only=True)
    name = serializers.CharField(source='ingredient.name', read_only=True)
    measurement_unit = serializers.CharField(
        source='ingredient.measurement_unit', read_only=True)
    amount = serializers.IntegerField(
        required=True, validators=[MinValueValidator(MIN_INGREDIENT_AMOUNT)])

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


class RecipeIngredientCreateSerializer(serializers.Serializer):
    """Сериализатор для обработки ингредиентов и их количества в рецепте."""

    id = serializers.IntegerField()
    amount = serializers.IntegerField(
        validators=[MinValueValidator(MIN_INGREDIENT_AMOUNT)])

    def validate_id(self, value):
        """Проверяем, что ингредиент с таким ID существует."""
        try:
            Ingredients.objects.get(id=value)
            return value
        except Ingredients.DoesNotExist:
            raise serializers.ValidationError(
                "Ингредиент с таким ID не найден.")


class RecipeSerializer(serializers.ModelSerializer):
    """Общий сериализатор для рецептов."""

    image = Base64ImageField(required=True)
    author = BaseUserSerializer(
        read_only=True, default=serializers.CurrentUserDefault())
    is_favorited = serializers.SerializerMethodField()
    is_in_shopping_cart = serializers.SerializerMethodField()
    tags = serializers.SerializerMethodField()
    ingredients = serializers.SerializerMethodField()

    def get_ingredients(self, obj):
        return RecipeIngredientSerializer(
            obj.recipeingredients_set.all(), many=True).data

    def get_tags(self, obj):
        return TagsSerializer(obj.tags.all(), many=True).data

    def get_is_favorited(self, obj):
        user = self.context.get('request').user
        return user.is_authenticated and Favorite.objects.filter(
            user=user, recipe=obj).exists()

    def get_is_in_shopping_cart(self, obj):
        user = self.context.get('request').user
        return user.is_authenticated and ShoppingCart.objects.filter(
            user=user, recipe=obj).exists()

    class Meta:
        """Meta."""

        model = Recipe
        fields = (
            'id', 'author', 'name', 'image', 'text', 'ingredients',
            'tags', 'cooking_time', 'is_favorited', 'is_in_shopping_cart',
        )


class RecipeCreateUpdateSerializer(serializers.ModelSerializer):
    """Сериализатор для создания и обновления рецептов."""

    image = Base64ImageField(required=True)
    author = BaseUserSerializer(
        read_only=True, default=serializers.CurrentUserDefault())
    ingredients = RecipeIngredientCreateSerializer(many=True)
    tags = serializers.PrimaryKeyRelatedField(
        queryset=Tags.objects.all(), many=True)

    class Meta:
        """Meta."""

        model = Recipe
        fields = (
            'id', 'author', 'name', 'image', 'text', 'ingredients',
            'tags', 'cooking_time',
        )

    def validate(self, data):
        """Валидация полей рецептов."""
        tags = data.get('tags')
        ingredients = data.get('ingredients')
        text = data.get('text')
        name = data.get('name')
        image = data.get('image')

        if not name:
            raise ValidationError({'name': ['Отсутствует название']})
        if not text:
            raise ValidationError({'text': ['Отсутствует описание рецепта']})
        if not image or image == '':
            raise ValidationError({'image': ['Отсутствует изображение']})

        if not tags:
            raise ValidationError(
                {'tags': ['Необходимо указать тег(-и)']})
        if len(tags) != len(set(tags)):
            raise ValidationError(
                {'tags': ['Теги не должны повторяться']})

        if not ingredients:
            raise ValidationError(
                {'ingredients': ['Ингредиенты должны быть указаны']})
        id_ingredients = [ingredient['id'] for ingredient in ingredients]
        if len(id_ingredients) != len(set(id_ingredients)):
            raise ValidationError(
                {'ingredients': ['Ингредиенты не должны повторяться']})
        return data

    def to_representation(self, instance):
        """Форматирование ответа с использованием RecipeSerializer."""
        return RecipeSerializer(instance, context=self.context).data

    def _create_recipe_ingredients(self, recipe, ingredients_data):
        ingredient_objects = []
        for ingredient_data in ingredients_data:
            serializer = RecipeIngredientCreateSerializer(data=ingredient_data)
            serializer.is_valid(raise_exception=True)
            ingredient_objects.append(RecipeIngredients(
                recipe=recipe,
                ingredient_id=serializer.validated_data['id'],
                amount=serializer.validated_data['amount']
            ))
        RecipeIngredients.objects.bulk_create(ingredient_objects)

    def create(self, validated_data):
        """Создание рецепта."""
        ingredients_data = validated_data.pop('ingredients')
        tags_data = validated_data.pop('tags')
        recipe = Recipe.objects.create(**validated_data)
        self._create_recipe_ingredients(recipe, ingredients_data)
        recipe.tags.set(tags_data)
        return recipe

    def update(self, instance, validated_data):
        """Обновление рецепта."""
        print(validated_data)
        ingredients_data = validated_data.pop('ingredients')
        tags_data = validated_data.pop('tags')
        RecipeIngredients.objects.filter(recipe=instance).delete()
        self._create_recipe_ingredients(instance, ingredients_data)
        instance.tags.set(tags_data)
        super().update(instance, validated_data)
        return instance
