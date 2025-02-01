"""Сериализаторы."""

from django.contrib.auth import password_validation
from django.core.validators import MinValueValidator
from drf_extra_fields.fields import Base64ImageField
from rest_framework import serializers
from rest_framework.exceptions import ValidationError

from api.constants import FORBIDDEN_USERNAME, MIN_INGREDIENT_AMOUNT
from recipes.models import (Favorite, Ingredient, ShoppingCart, Subscription,
                            RecipeIngredient, Recipe, Tag, User)


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
        return user.is_authenticated and Subscription.objects.filter(
            user=user, subscriber=obj).exists()

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
        if recipes_limit and recipes_limit.isdigit():
            recipes = recipes[:int(recipes_limit)]
        return ShortRecipeSerializer(
            recipes, many=True, context=self.context
        ).data

    def get_recipes_count(self, obj):
        return obj.recipes.count()


class SubscriptionSerializer(serializers.Serializer):
    """Сериализатор для создания и удаления подписок."""

    def validate(self, data):
        """Валидация автора и подписок."""
        user = self.context['request'].user
        author = self.context.get('author')
        if user == author:
            raise serializers.ValidationError(
                'Нельзя подписаться на самого себя.')
        method = self.context['request'].method
        if method == 'POST':
            if Subscription.objects.filter(
                    user=user, subscriber=author).exists():
                raise serializers.ValidationError(
                    'Вы уже подписаны на этого автора.')
        if method == 'DELETE':
            if not Subscription.objects.filter(
                    user=user, subscriber=author).exists():
                raise serializers.ValidationError(
                    'Вы не подписаны на пользователя.')
        return data

    def create(self, validated_data):
        """Подписываемся."""
        user = self.context['request'].user
        author = self.context.get('author')
        subscription = Subscription.objects.create(
            user=user, subscriber=author)
        return subscription

    def delete(self):
        """Отписываемся."""
        user = self.context['request'].user
        author = self.context.get('author')
        Subscription.objects.filter(user=user, subscriber=author).delete()

    def to_representation(self, instance):
        """Возвращает данные о подписке."""
        request = self.context.get('request')
        recipes_limit = request.query_params.get('recipes_limit')
        serializer = SubscribedUserSerializer(
            instance.subscriber, context={
                'request': request, 'recipes_limit': recipes_limit})
        return serializer.data


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

        model = Ingredient
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
        model = RecipeIngredient
        fields = ('id', 'name', 'measurement_unit', 'amount')


class TagsSerializer(serializers.ModelSerializer):
    """Сериализатор рецептов."""

    name = serializers.ReadOnlyField()
    slug = serializers.ReadOnlyField()

    class Meta:
        """Meta."""

        model = Tag
        fields = ('id', 'name', 'slug')


class BaseFavoriteShoppingCartCerializer(serializers.Serializer):
    """Базовый класс для сериализаторов избранного и списка покупок."""

    def validate(self, data):
        """Валидация по типу запроса."""
        model = self.Meta.model
        user = self.context['request'].user
        recipe = self.context.get('recipe')
        method = self.context['request'].method
        if method == 'POST':
            if model.objects.filter(user=user, recipe=recipe).exists():
                raise serializers.ValidationError(
                    f'{recipe.name!r} уже добавлен в список.')
        if method == 'DELETE':
            if not model.objects.filter(user=user, recipe=recipe).exists():
                raise serializers.ValidationError(
                    f'{recipe.name!r} нет в списке.')
        return data

    def get_object_data(self):
        user = self.context['request'].user
        model = self.Meta.model
        recipe = self.context.get('recipe')
        return user, model, recipe

    def create(self, validated_data):
        """Создаем объект."""
        user, model, recipe = self.get_object_data()
        new_obj = model.objects.create(user=user, recipe=recipe)
        return new_obj

    def delete(self):
        """Удаляем объект."""
        user, model, recipe = self.get_object_data()
        model.objects.filter(user=user, recipe=recipe).delete()

    def to_representation(self, instance):
        """Возвращает данные об объекте."""
        request = self.context.get('request')
        serializer = ShortRecipeSerializer(
            instance.recipe, context={'request': request})
        return serializer.data


class ShoppingCartSerializer(BaseFavoriteShoppingCartCerializer):
    """Сериализатор для создания и удаления рецепта из списка покупок."""

    class Meta:
        model = ShoppingCart
        model_name = 'recipe'


class FavoriteSerializer(BaseFavoriteShoppingCartCerializer):
    """Сериализатор для добавления/удаления рецепта в избранное."""

    class Meta:
        model = Favorite
        model_name = 'recipe'


class RecipeIngredientCreateSerializer(serializers.Serializer):
    """Сериализатор для обработки ингредиентов и их количества в рецепте."""

    id = serializers.IntegerField()
    amount = serializers.IntegerField(
        validators=[MinValueValidator(MIN_INGREDIENT_AMOUNT)])

    def validate_id(self, value):
        """Проверяем, что ингредиент с таким ID существует."""
        if not Ingredient.objects.filter(id=value).exists():
            raise serializers.ValidationError(
                "Ингредиент с таким ID не найден.")
        return value


class RecipeSerializer(serializers.ModelSerializer):
    """Общий сериализатор для рецептов."""

    image = Base64ImageField(required=True)
    author = BaseUserSerializer(
        read_only=True, default=serializers.CurrentUserDefault())
    is_favorited = serializers.SerializerMethodField()
    is_in_shopping_cart = serializers.SerializerMethodField()
    tags = TagsSerializer(many=True)
    ingredients = RecipeIngredientSerializer(
        many=True, source='recipeingredient_set')

    class Meta:
        """Meta."""

        model = Recipe
        fields = (
            'id', 'author', 'name', 'image', 'text', 'ingredients',
            'tags', 'cooking_time', 'is_favorited', 'is_in_shopping_cart')

    def get_is_favorited(self, obj):
        user = self.context.get('request').user
        return user.is_authenticated and obj.favorites.filter(
            user=user).exists()

    def get_is_in_shopping_cart(self, obj):
        user = self.context.get('request').user
        return user.is_authenticated and obj.shopping_carts.filter(
            user=user).exists()


class RecipeCreateUpdateSerializer(serializers.ModelSerializer):
    """Сериализатор для создания и обновления рецептов."""

    image = Base64ImageField(required=True)
    author = BaseUserSerializer(
        read_only=True, default=serializers.CurrentUserDefault())
    ingredients = RecipeIngredientCreateSerializer(many=True)
    tags = serializers.PrimaryKeyRelatedField(
        queryset=Tag.objects.all(), many=True)

    class Meta:
        """Meta."""

        model = Recipe
        fields = (
            'id', 'author', 'name', 'image', 'text', 'ingredients',
            'tags', 'cooking_time')

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
        ingredient_objects = [
            RecipeIngredient(
                recipe=recipe,
                ingredient_id=ingredient_data['id'],
                amount=ingredient_data['amount'])
            for ingredient_data in ingredients_data]
        RecipeIngredient.objects.bulk_create(ingredient_objects)

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
        ingredients_data = validated_data.pop('ingredients')
        tags_data = validated_data.pop('tags')
        RecipeIngredient.objects.filter(recipe=instance).delete()
        self._create_recipe_ingredients(instance, ingredients_data)
        instance.tags.set(tags_data)
        return super().update(instance, validated_data)
