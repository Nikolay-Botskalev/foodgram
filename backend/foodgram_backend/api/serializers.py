"""Сериализаторы."""

import base64
from smtplib import SMTPException
from random import randint

from django.core.files.base import ContentFile
from django.core.mail import send_mail
from django.shortcuts import get_object_or_404
from rest_framework import serializers
from rest_framework.exceptions import APIException
from rest_framework_simplejwt.tokens import AccessToken
from rest_framework.exceptions import ValidationError

from recipes.models import (
    Ingredients, Recipes, MyUser, Tags, RecipeIngredients)


EMAIL_SUBJECT = 'Код для получения токена авторизации'
EMAIL_SOURCE = 'serzh.mironov1990.mironov@mail.ru'
EMAIL_ERROR = 'Произошла следующая ошибка при попытке отправки письма:\n'


class ValidateUsernameMixin:
    """Миксин, запрещающий пользователю создать username "me"."""

    def validate_username(self, value):
        if value.lower() == 'me':
            raise serializers.ValidationError(
                'Используйте другой username.'
            )
        return value


class BaseUserSerializer(serializers.ModelSerializer):

    class Meta:
        model = MyUser
        fields = ('id', 'username', 'email', 'first_name', 'last_name',
                  'avatar', 'is_subscribed')
        read_only_fields = ('password',)


class SignUpSerializer(ValidateUsernameMixin, serializers.ModelSerializer):
    """Сериализатор для эндпоинта api/v1/auth/signup/"""

    class Meta:
        model = MyUser
        fields = ('username', 'email', 'first_name', 'last_name', 'password')
        extra_kwargs = {'password': {'write_only': True}}

    def create(self, validated_data):
        """Метод создаёт нового пользователя."""
        username = validated_data['username']
        email = validated_data['email']
        first_name = validated_data['first_name']
        last_name = validated_data['last_name']
        # получаем кортеж с юзером и bool значением (создано/не создано)
        user, created = MyUser.objects.get_or_create(
            username=username,
            email=email,
            first_name=first_name,
            last_name=last_name,
        )
        if not created:
            raise APIException("Пользователь с такими данными существует.")

        confirmation_code = self.send_code(email)
        user.confirmation_code = confirmation_code
        user.set_unusable_password()
        user.save()
        return user

    def update(self, instance, validated_data):
        """Метод создаёт пользователю новый код."""
        confirmation_code = self.send_code(validated_data.get('email'))
        instance.confirmation_code = confirmation_code
        instance.save()
        return instance

    def send_code(self, recipient_email):
        """Отправка письма с кодом подтверждения."""
        confirmation_code = randint(100000, 999999)
        message = f'Код для получения токена - {confirmation_code}'
        try:
            send_mail(
                EMAIL_SUBJECT,
                message,
                EMAIL_SOURCE,
                (recipient_email,),
                fail_silently=True
            )
        except SMTPException as error:
            raise APIException(EMAIL_ERROR + error)
        return confirmation_code


class GetTokenSerializer(serializers.Serializer):
    """Сериализатор для получения пользователем токена."""

    username = serializers.CharField(write_only=True)
    confirmation_code = serializers.IntegerField(write_only=True)

    def validate(self, data):
        user = get_object_or_404(MyUser, username=data['username'])
        if data['confirmation_code'] != user.confirmation_code:
            raise serializers.ValidationError('Неверный код подтверждения')
        data['token'] = str(AccessToken.for_user(user))
        return data


class UserSerializer(ValidateUsernameMixin, BaseUserSerializer):
    """Позволяет пользователю взаимодействовать со своими данными."""

    is_subscribed = serializers.SerializerMethodField(default=False)
    # recipes_count = serializers.SerializerMethodField()
    # recipes = serializers.StringRelatedField(read_only=True, many=True)
    avatar = serializers.SerializerMethodField()

    def get_is_subscribed(self, obj):
        user = self.context.get('request').user
        if user.is_anonymous:
            return False
        try:
            return user.following.filter(id=obj.id).exists()
        except AttributeError:
            return False

    def get_recipes_count(self, obj):
        return obj.recipes.count()

    def get_recipes(self, obj):
        return RecipesReadSerializer(
            obj.recipes.all(), many=True, context=self.context).data

    def get_avatar(self, obj):
        if obj.avatar:
            return self.context.get(
                'request').build_absolute_uri(obj.avatar.url)
        return None


class SubscribedUserSerializer(ValidateUsernameMixin, BaseUserSerializer):
    """Сериализатор для вывода информации о подписках."""

    is_subscribed = serializers.SerializerMethodField(default=True)
    recipes = serializers.SerializerMethodField()
    recipes_count = serializers.SerializerMethodField()
    avatar = serializers.SerializerMethodField()

    def get_is_subscribed(self, obj):
        return True

    def get_recipes(self, obj):
        return ShortRecipeSerializer(
            obj.recipes.all(), many=True, context=self.context).data

    def get_recipes_count(self, obj):
        return obj.recipes.count()

    def get_avatar(self, obj):
        if obj.avatar:
            return self.context.get('request').build_absolute_uri(
                obj.avatar.url)
        return None

    class Meta:

        model = MyUser
        fields = ('id', 'username', 'email', 'first_name', 'last_name','avatar', 'is_subscribed', 'recipes', 'recipes_count')


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

    ingredient = IngredientsSerializer(read_only=True)
    name = serializers.ReadOnlyField()
    measurement_unit = serializers.ReadOnlyField()
    amount = serializers.DecimalField(max_digits=6, decimal_places=2, read_only=True)
    #amount = serializers.DecimalField(max_digits=6, decimal_places=2, read_only=True)
    #name = serializers.CharField(source='ingredient.name', read_only=True)
    #measurement_unit = serializers.CharField(source='ingredient.measurement_unit', read_only=True)

    class Meta:
        model = RecipeIngredients
        fields = ('id', 'amount', 'ingredient', 'name', 'measurement_unit')
        read_only_fields = ('id',)


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

    image = Base64Image(required=False, allow_null=True)
    author = UserSerializer(
        read_only=True, default=serializers.CurrentUserDefault())
    is_favorited = serializers.SerializerMethodField(default=False)
    is_in_shopping_cart = serializers.SerializerMethodField(default=False)
    ingredients = RecipeIngredientSerializer(many=True, read_only=True)

    class Meta:
        """Meta."""

        model = Recipes
        fields = (
            'id', 'author', 'name', 'image', 'text', 'ingredients',
            'tags', 'cooking_time', 'is_favorited', 'is_in_shopping_cart',
        )
        read_only_fields = (
            'id', 'is_favorited', 'is_in_shopping_cart', 'author')
        unique_together = ['name', 'author', 'text']

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


class RecipesReadSerializer(RecipeSerializer):
    """Сериализатор для чтения рецептов."""

    # ingredients = RecipeIngredientSerializer(many=True)
    tags = TagsSerializer(many=True, read_only=True)


class RecipesWriteSerializer(RecipeSerializer):
    """Сериализатор для создания/обновления рецептов."""

    ingredients = RecipeIngredientSerializer(many=True)
    tags = TagsSerializer(many=True, read_only=True)

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
                        {'classes': ['Invalid classes primary key']},
                        code='invalid',
                    )
        internal_data['tags'] = tags
        internal_data['ingredients'] = ingredients
        return internal_data

    def create_recipe_ingredients(self, recipe, ingredients):
        RecipeIngredients.objects.bulk_create(
            [
                RecipeIngredients(
                    ingredient=Ingredients.objects.get(
                        id=ingredient.get('id')),
                    recipe=recipe,
                    amount=ingredient.get('amount')
                )
                for ingredient in ingredients
            ]
        )

    def create(self, validated_data):
        tags = validated_data.pop('tags')
        ingredients = validated_data.pop('ingredients')
        recipe = Recipes.objects.create(**validated_data)
        recipe.tags.set(tags)
        self.create_recipe_ingredients(recipe, ingredients)
        return recipe
