"""Вьюсеты."""

from hashids import Hashids

from django.conf import settings
from django.contrib.auth import authenticate
from django.db.models import Sum
from django.http import FileResponse
from django.shortcuts import get_object_or_404, redirect
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import status, viewsets
from rest_framework.authtoken.models import Token
from rest_framework.decorators import action
from rest_framework.filters import OrderingFilter, SearchFilter
from rest_framework.pagination import LimitOffsetPagination
from rest_framework.permissions import (AllowAny, IsAuthenticated,
                                        IsAuthenticatedOrReadOnly)
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.viewsets import ModelViewSet

from api.constants import MIN_LENGTH_HASH_CODE
from api.filters import IngredientFilter, RecipeFilter
from api.permissions import IsAuthorOrReadOnly
from api.serializers import (AvatarSerializer, BaseUserSerializer,
                             FavoriteSerializer, IngredientsSerializer,
                             LoginSerializer, RecipeCreateUpdateSerializer,
                             RecipeSerializer, SetPasswordSerializer,
                             ShoppingCartSerializer, ShortRecipeSerializer,
                             SubscribedUserSerializer, SubscriptionSerializer,
                             TagsSerializer, UserCreateSerializer,
                             UserRegistrationSerializer)
from recipes.models import (Ingredient, RecipeIngredient, Recipe, ShoppingCart,
                            Tag, User)

hashids = Hashids(min_length=MIN_LENGTH_HASH_CODE, salt=settings.SECRET_KEY)


class LoginView(APIView):
    """Получение токена."""

    permission_classes = (AllowAny,)

    def post(self, request):
        """Получение токена авторизации по email и паролю."""
        serializer = LoginSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        email = serializer.validated_data['email']
        password = serializer.validated_data['password']

        user = authenticate(username=email, password=password)

        if user is None:
            return Response(
                {'error': 'Неверный email или пароль'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        token, _ = Token.objects.get_or_create(user=user)
        return Response({'auth_token': token.key})


class LogoutView(APIView):
    """Удаление токена."""

    permission_classes = (IsAuthenticated,)

    def post(self, request):
        """Удаление токена."""
        user = request.user
        Token.objects.filter(user=user).delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


def handle_action(request, pk, model, serializer, context_key, viewset):
    """Реализована общая логика методов favorite, shopping_cart, subscribe."""
    obj = get_object_or_404(model, pk=pk)
    context = {'request': request, context_key: obj}
    if request.method == 'POST':
        serializer = serializer(
            data=request.data, context=context)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    serializer = serializer(
        data=request.data, context=context)
    serializer.is_valid(raise_exception=True)
    serializer.delete()
    return Response(status=status.HTTP_204_NO_CONTENT)


class UserViewSet(ModelViewSet):
    """View для запросов к пользователям."""

    queryset = User.objects.all()
    serializer_class = BaseUserSerializer
    permission_classes = (AllowAny,)
    pagination_class = LimitOffsetPagination
    filter_backends = (SearchFilter, OrderingFilter)
    search_fields = ('recipes__tags__slug', 'username',)
    ordering_fields = ('username',)
    http_method_names = ('get', 'post', 'put', 'delete')

    def get_permissions(self):
        """Установка прав доступа."""
        permission_classes_map = {
            'me': (IsAuthenticated,),
            'avatar': (IsAuthenticated,),
            'subscriptions': (IsAuthenticated,),
            'subscribe': (IsAuthenticated,),
            'recipes': (AllowAny,),
            'create': (AllowAny,),
            'set_password': (IsAuthenticated,)
        }
        return [permission() for permission in permission_classes_map.get(
            self.action, self.permission_classes)]

    def create(self, request, *args, **kwargs):
        """Создание пользователя."""
        serializer = UserCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        response_serializer = UserRegistrationSerializer(serializer.instance)
        headers = self.get_success_headers(response_serializer.data)
        return Response(
            response_serializer.data,
            status=status.HTTP_201_CREATED,
            headers=headers)

    def recipes(self, request, pk=None):
        """Получение списка рецептов пользователя."""
        user = self.get_object()
        queryset = Recipe.objects.filter(author=user).order_by('-pub_date')
        queryset = self.filter_queryset(queryset)
        serializer = ShortRecipeSerializer(queryset, many=True)
        return Response(serializer.data)

    def perform_create(self, serializer):
        user = serializer.save()
        user.set_password(serializer.validated_data['password'])
        user.save()

    @action(detail=False, methods=['get'])
    def me(self, request):
        """Получение своих данных."""
        user = request.user
        serializer = self.get_serializer(user)
        return Response(serializer.data)

    @action(detail=False, methods=['post'])
    def set_password(self, request):
        """Изменение пароля пользователя."""
        serializer = SetPasswordSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        new_password = request.data.get('new_password')
        current_password = request.data.get('current_password')
        user = request.user
        if not authenticate(username=user.email, password=current_password):
            return Response(
                {'error': 'Неверный текущий пароль'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        user.set_password(new_password)
        user.save()
        return Response(
            {'message': 'Пароль успешно изменен'},
            status=status.HTTP_204_NO_CONTENT)

    @action(detail=False, methods=['put', 'delete'], url_path='me/avatar')
    def avatar(self, request):
        """Изменение/удаление аватара."""
        user = request.user
        if request.method == 'PUT':
            serializer = AvatarSerializer(user, data=request.data)
            serializer.is_valid(raise_exception=True)
            serializer.save()
            return Response(serializer.data)
        user.avatar = None
        user.save()
        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(detail=False, methods=['get'])
    def subscriptions(self, request):
        """Получение списка подписок."""
        user = request.user
        queryset = User.objects.filter(subscribers__user=user)
        recipes_limit = request.query_params.get('recipes_limit')
        page = self.paginate_queryset(queryset)
        serializer = SubscribedUserSerializer(
            page, many=True, context={
                'request': request, 'recipes_limit': recipes_limit})
        return self.get_paginated_response(serializer.data)

    @action(detail=True, methods=['post', 'delete'])
    def subscribe(self, request, pk=None):
        """Подписка/отписка на пользователя."""
        return handle_action(
            request, pk, User, SubscriptionSerializer, 'author', self)


class ReciepesViewSet(viewsets.ModelViewSet):
    """Вьюсет для обработки запросов к рецептам."""

    queryset = Recipe.objects.all().order_by('-pub_date')
    serializer_class = RecipeSerializer
    permission_classes = (IsAuthenticatedOrReadOnly, IsAuthorOrReadOnly)
    pagination_class = LimitOffsetPagination
    filter_backends = (DjangoFilterBackend, SearchFilter, OrderingFilter)
    filterset_class = RecipeFilter
    http_method_names = ('get', 'post', 'patch', 'delete')

    def perform_create(self, serializer):
        serializer.save(author=self.request.user)

    def get_permissions(self):
        """Установка прав доступа."""
        permission_classes_map = {
            'get_link': (AllowAny,),
            'retrieve': (AllowAny,),
            'shopping_cart': (IsAuthenticated,),
            'download_shopping_cart': (IsAuthenticated,),
            'favorite': (IsAuthenticated,),
            'update': (IsAuthorOrReadOnly,),
            'destroy': (IsAuthorOrReadOnly,),
            'create': (IsAuthenticated,),
        }
        return [permission() for permission in permission_classes_map.get(
            self.action, self.permission_classes)]

    def get_serializer_class(self):
        if self.action in ('create', 'update', 'partial_update'):
            return RecipeCreateUpdateSerializer
        return RecipeSerializer

    @action(detail=True, methods=['post', 'delete'])
    def shopping_cart(self, request, pk=None):
        """Метод для добавления/удаления рецепта в список покупок."""
        return handle_action(
            request, pk, Recipe, ShoppingCartSerializer, 'recipe', self)

    def get_shopping_cart_data(self, user):
        """Формирование данных для списка покупок."""
        recipe_cart = ShoppingCart.objects.filter(
            user=user).values_list('recipe', flat=True)
        return RecipeIngredient.objects.filter(
            recipe__in=recipe_cart).values(
            'ingredient__name', 'ingredient__measurement_unit'
        ).annotate(amount=Sum('amount')).order_by('recipe__name')

    def create_shopping_cart_text(self, queryset):
        """Формирование текста для списка покупок."""
        return '\n'.join(
            f"{data['ingredient__name'].capitalize()} - {data['amount']} "
            f"{data['ingredient__measurement_unit']}."
            for data in queryset)

    @action(detail=False, methods=['get'])
    def download_shopping_cart(self, request):
        """Метод для скачивания списка покупок."""
        user = request.user
        queryset = self.get_shopping_cart_data(user)
        shopping_cart_text = self.create_shopping_cart_text(queryset)
        response = FileResponse(
            shopping_cart_text, content_type='text/plain')
        response['Content-Disposition'] = 'attachment; filename="cart.txt"'
        return response

    @action(detail=True, methods=['post', 'delete'])
    def favorite(self, request, pk=None):
        """Метод для добавления/удаления рецепта в избранное."""
        return handle_action(
            request, pk, Recipe, FavoriteSerializer, 'recipe', self)

    @action(detail=True, methods=['get'], url_path='get-link')
    def get_link(self, request, pk=None):
        """Метод для возврата короткой ссылки."""
        recipe = get_object_or_404(Recipe, pk=pk)
        short_id = hashids.encode(recipe.pk)
        url = f'/api/{short_id}'
        absolut_url = request.build_absolute_uri(url)
        return Response(
            {'short-link': absolut_url},
            status=status.HTTP_200_OK)


def short_link_redirect(request, string):
    """Метод для редиректа с короткой ссылки."""
    try:
        recipe_id = hashids.decode(string)[0]
        if not recipe_id:
            return Response(status=status.HTTP_404_NOT_FOUND)
        recipe = get_object_or_404(Recipe, pk=recipe_id)
        return redirect(f'recipes/{recipe.pk}/')
    except (IndexError, ValueError):
        return Response(status=status.HTTP_404_NOT_FOUND)


class IngredientsViewSet(viewsets.ReadOnlyModelViewSet):
    """Вьюсет для обработки запросов к ингредиентам."""

    queryset = Ingredient.objects.all()
    serializer_class = IngredientsSerializer
    permission_classes = (AllowAny,)
    pagination_class = None
    filter_backends = (DjangoFilterBackend,)
    filterset_class = IngredientFilter


class TagsViewSet(viewsets.ReadOnlyModelViewSet):
    """Вьюсет для обработки запросов к тегам."""

    queryset = Tag.objects.all()
    serializer_class = TagsSerializer
    permission_classes = (AllowAny,)
    pagination_class = None
    filter_backends = (SearchFilter, OrderingFilter)
    search_fields = ('slug',)
    ordering_fields = ('name',)
