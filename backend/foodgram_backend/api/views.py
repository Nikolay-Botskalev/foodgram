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

from api.filters import IngredientFilter, RecipeFilter
from api.permissions import IsAuthorOrReadOnly
from api.serializers import (AvatarSerializer, BaseUserSerializer,
                             IngredientsSerializer, LoginSerializer,
                             RecipeCreateUpdateSerializer, RecipeSerializer,
                             SetPasswordSerializer, ShortRecipeSerializer,
                             SubscribedUserSerializer, SubscriptionSerializer,
                             TagsSerializer, UserCreateSerializer,
                             UserRegistrationSerializer)
from recipes.models import (Favorite, Ingredients, RecipeIngredients, Recipe,
                            ShoppingCart, Subscription, Tags, User)

hashids = Hashids(min_length=5, salt=settings.SECRET_KEY)


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

    @action(detail=True, methods=['get'])
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
        if page is not None:
            serializer = SubscribedUserSerializer(
                page, many=True, context={
                    'request': request, 'recipes_limit': recipes_limit}
            )
            return self.get_paginated_response(serializer.data)
        else:
            serializer = SubscribedUserSerializer(
                queryset, many=True, context={
                    'request': request, 'recipes_limit': recipes_limit}
            )
            return Response(serializer.data)

    @action(detail=True, methods=['post', 'delete'])
    def subscribe(self, request, pk=None):
        """Подписка/отписка на пользователя."""
        subscriber = request.user
        user_to_follow = get_object_or_404(User, id=pk)
        recipes_limit = request.query_params.get('recipes_limit')
        if request.method == 'POST':
            if Subscription.objects.filter(
                    user=subscriber, subscriber=user_to_follow).exists():
                return Response(
                    {'errors': 'Вы уже подписаны на этого пользователя'},
                    status=status.HTTP_400_BAD_REQUEST)
            if subscriber == user_to_follow:
                return Response(
                    {'detail': ['Вы не можете подписаться на самого себя.']},
                    status=status.HTTP_400_BAD_REQUEST
                )

            _ = Subscription.objects.create(user=subscriber,
                                            subscriber=user_to_follow)
            return Response(
                SubscriptionSerializer(
                    user_to_follow, context={
                        'request': request, 'recipes_limit': recipes_limit}
                ).data, status=status.HTTP_201_CREATED)

        if not Subscription.objects.filter(
                user=subscriber, subscriber=user_to_follow).exists():
            return Response({'errors': 'Вы не подписаны на пользователя'},
                            status=status.HTTP_400_BAD_REQUEST)
        Subscription.objects.filter(
            user=subscriber, subscriber=user_to_follow).delete()
        return Response(status=status.HTTP_204_NO_CONTENT)

    def get_object(self):
        return get_object_or_404(self.queryset, pk=self.kwargs['pk'])


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
        user = request.user
        recipe = get_object_or_404(Recipe, id=pk)
        if request.method == 'POST':
            if ShoppingCart.objects.filter(user=user, recipe=recipe).exists():
                return Response({'errors': 'Рецепт уже в списке покупок'},
                                status=status.HTTP_400_BAD_REQUEST)
            ShoppingCart.objects.create(user=user, recipe=recipe)
            return Response(
                ShortRecipeSerializer(
                    recipe, context={'request': request}
                ).data, status=status.HTTP_201_CREATED)
        if not ShoppingCart.objects.filter(user=user, recipe=recipe).exists():
            return Response({'errors': 'Рецепта нет в списке покупок'},
                            status=status.HTTP_400_BAD_REQUEST)
        ShoppingCart.objects.filter(user=user, recipe=recipe).delete()
        return Response(status=status.HTTP_204_NO_CONTENT)

    def get_shopping_cart_list(self, user):
        """Формирование данных для списка покупок."""
        recipe_cart = ShoppingCart.objects.filter(
            user=user).values_list('recipe', flat=True)
        return RecipeIngredients.objects.filter(
            recipe__in=recipe_cart).values(
            'ingredient__name', 'ingredient__measurement_unit'
        ).annotate(amount=Sum('amount'))

    @action(detail=False, methods=['get'])
    def download_shopping_cart(self, request):
        """Метод для скачивания списка покупок."""
        user = request.user
        queryset = self.get_shopping_cart_list(user)
        shopping_cart_text = '\n'.join(
            f"{data['ingredient__name'].capitalize()} - {data['amount']} "
            f"{data['ingredient__measurement_unit']}."
            for data in queryset
        )
        response = FileResponse(
            shopping_cart_text, content_type='text/plain')
        response['Content-Disposition'] = 'attachment; filename="cart.txt"'
        return response

    @action(detail=True, methods=['post', 'delete'])
    def favorite(self, request, pk=None):
        """Добавление/удаление рецепта в избранное."""
        recipe = get_object_or_404(Recipe, id=pk)
        user = request.user
        if request.method == 'POST':
            if Favorite.objects.filter(user=user, recipe=recipe).exists():
                return Response(
                    {'errors': 'Рецепт уже есьт в избранном'},
                    status=status.HTTP_400_BAD_REQUEST
                )

            Favorite.objects.create(user=user, recipe=recipe)
            return Response(
                ShortRecipeSerializer(
                    recipe, context={'request': request}
                ).data, status=status.HTTP_201_CREATED)
        if not Favorite.objects.filter(user=user, recipe=recipe).exists():
            return Response({'errors': 'Рецепта нет в избранном'},
                            status=status.HTTP_400_BAD_REQUEST)
        Favorite.objects.filter(user=user, recipe=recipe).delete()
        return Response(status=status.HTTP_204_NO_CONTENT)

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

    queryset = Ingredients.objects.all()
    serializer_class = IngredientsSerializer
    permission_classes = (AllowAny,)
    http_method_names = ('get',)
    pagination_class = None
    filter_backends = (DjangoFilterBackend,)
    filterset_class = IngredientFilter


class TagsViewSet(viewsets.ReadOnlyModelViewSet):
    """Вьюсет для обработки запросов к тегам."""

    queryset = Tags.objects.all()
    serializer_class = TagsSerializer
    permission_classes = (AllowAny,)
    pagination_class = None
    filter_backends = (SearchFilter, OrderingFilter)
    search_fields = ('slug',)
    ordering_fields = ('name',)
    http_method_names = ('get',)
