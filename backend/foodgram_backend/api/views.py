"""Вьюсеты."""

from django.conf import settings
from django.http import HttpResponse
from django.shortcuts import get_object_or_404
from rest_framework import generics, status, viewsets
from rest_framework.decorators import action
from rest_framework.filters import OrderingFilter, SearchFilter
from rest_framework.mixins import (CreateModelMixin,)
from rest_framework.permissions import (
    AllowAny, IsAuthenticated, IsAuthenticatedOrReadOnly)
from rest_framework.response import Response
from rest_framework.pagination import PageNumberPagination
from rest_framework_simplejwt.exceptions import InvalidToken, TokenError
from rest_framework_simplejwt.views import TokenObtainPairView
from rest_framework.views import APIView
from rest_framework.viewsets import GenericViewSet, ModelViewSet

from recipes.models import (
    Ingredients, MyUser, Recipes, Tags, RecipeIngredients)
from .permissions import IsAuthorOrReadOnly
from .serializers import (
    AvatarSerializer,
    GetTokenSerializer,
    IngredientsSerializer,
    RecipeSerializer,
    ShortRecipeSerializer,
    SignUpSerializer,
    SubscribedUserSerializer,
    TagsSerializer,
    UserSerializer,
)


class SignUpViewSet(CreateModelMixin, GenericViewSet):
    """ViewSet, обслуживающий эндпоинт api/v1/auth/signup/."""

    queryset = MyUser.objects.all()
    serializer_class = SignUpSerializer
    permission_classes = (AllowAny,)

    def create(self, request, *args, **kwargs):
        """
        Если такого пользователя с заданными username и email
        не существует, то создаем.
        Если пользователь с заданными username и email
        существует, то сериализатор обновляет его confirmation_code.
        """
        try:
            user = MyUser.objects.get(
                username=request.data.get('username'),
                email=request.data.get('email'),
                first_name=request.data.get('first_name'),
                last_name=request.data.get('last_name'))
            serializer = self.get_serializer(user, data=request.data)
        except MyUser.DoesNotExist:
            serializer = self.get_serializer(data=request.data)

        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        headers = self.get_success_headers(serializer.data)
        return Response(
            serializer.data, status=status.HTTP_200_OK, headers=headers
        )


class GetTokenView(TokenObtainPairView):
    """ViewSet для получения токенов."""

    serializer_class = GetTokenSerializer
    http_method_names = ('post',)

    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        try:
            serializer.is_valid(raise_exception=True)
        except TokenError as err:
            raise InvalidToken(err.args[0])

        return Response(
            {'token': serializer.validated_data['token']},
            status=status.HTTP_200_OK
        )


class UserViewSet(ModelViewSet):
    """View для управления пользователями администраторами."""

    queryset = MyUser.objects.all()
    serializer_class = UserSerializer
    permission_classes = (IsAuthenticated,)
    pagination_class = PageNumberPagination
    filter_backends = (SearchFilter, OrderingFilter)
    search_fields = ('username',)
    ordering_fields = ('username',)
    http_method_names = ('get', 'post', 'put', 'delete')

    def perform_create(self, serializer):
        user = serializer.save()
        user.set_unusable_password()
        user.save()

    def get_object(self):
        return get_object_or_404(self.queryset, pk=self.kwargs['pk'])


class MeUserView(generics.RetrieveAPIView, generics.UpdateAPIView):
    """View для просмотра и редактирования пользователем своих данных."""

    serializer_class = UserSerializer
    permission_classes = (IsAuthenticated,)

    def get_object(self):
        return self.request.user

    def perform_update(self, serializer):
        serializer.save()


class MeUserAvatarView(generics.UpdateAPIView, generics.DestroyAPIView):
    """View для изменения/удаления аватара."""

    serializer_class = AvatarSerializer
    permission_classes = (IsAuthenticated,)
    http_method_names = ('put', 'delete')

    def get_object(self):
        return self.request.user

    def perform_update(self, serializer):
        serializer.save()

    def perform_destroy(self, instance):
        instance.avatar = None
        instance.save()


class MeUserFollowingView(generics.ListAPIView):
    """View для извлечения всех подписок."""

    serializer_class = SubscribedUserSerializer
    permission_classes = (IsAuthenticated,)
    http_method_names = ('get',)

    def get_queryset(self):
        return self.request.user.is_subscribed.all()


class FollowingView(APIView):
    """View для работы с подписками."""

    permission_classes = (IsAuthenticated,)
    http_method_names = ('post', 'delete')

    def post(self, request, pk):
        user_to_following = get_object_or_404(MyUser, id=pk)
        request.user.is_subscribed.add(user_to_following)
        serializer = SubscribedUserSerializer(
            user_to_following, context={'request': request})
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    def delete(self, request, pk):
        user_to_unsubscribe = get_object_or_404(MyUser, id=pk)
        request.user.is_subscribed.remove(user_to_unsubscribe)
        return Response(
            {'message': 'Отписка'}, status=status.HTTP_204_NO_CONTENT)


class ReciepesViewSet(viewsets.ModelViewSet):
    """Вьюсет для обработки запросов к рецептам."""

    queryset = Recipes.objects.all()
    serializer_class = RecipeSerializer
    permission_classes = (IsAuthenticatedOrReadOnly, IsAuthorOrReadOnly)
    pagination_class = PageNumberPagination
    filter_backends = (SearchFilter, OrderingFilter)
    search_fields = ('name',)
    ordering_fields = ('id',)
    http_method_names = ('get', 'post', 'patch', 'delete')

    def perform_create(self, serializer):
        serializer.save(author=self.request.user)

    def perform_update(self, serializer):
        instance = serializer.save()
        return instance

    def get_permissions(self):
        if self.action == 'get_link':
            permission_classes = (AllowAny,)
        elif self.action in (
            'add_to_shopping_cart',
            'remove_from_shopping_cart',
            'download_shopping_cart',
            'add_to_favorite',
            'remove_from_favorite'
        ):
            permission_classes = (IsAuthenticated,)
        elif self.action in ('update', 'delete'):
            permission_classes = (IsAuthorOrReadOnly,)
        else:
            permission_classes = self.permission_classes
        return [permission() for permission in permission_classes]

    @action(detail=True, methods=['get'])
    def get_link(self, request, pk=None):
        """Метод для возврата короткой ссылки."""
        recipe = get_object_or_404(Recipes, pk=pk)
        return Response(
            {'short-link': f'{settings.BASE_URL}/api/recipes/{recipe.pk}'},
            status=status.HTTP_200_OK)

    @action(detail=True, methods=['post'])
    def add_to_shopping_cart(self, request, pk=None):
        """Метод для добавления рецепта в список покупок."""
        print(request)
        recipe = self.get_object()
        user = request.user
        user.shopping_cart.add(recipe)
        return Response(
            {'message': 'Рецепт успешно добавлен в список покупок'},
            status=status.HTTP_201_CREATED)

    @action(detail=True, methods=['delete'])
    def remove_from_shopping_cart(self, request, pk=None):
        """Метод для удаления рецепта из списка покупок."""
        recipe = self.get_object()
        user = request.user
        user.shopping_cart.remove(recipe)
        return Response(
            {'message': 'Рецепт успешно удален из списка покупок'},
            status=status.HTTP_204_NO_CONTENT)

    @action(detail=True, methods=['get'])
    def download_shopping_cart(self, request):
        """Метод для скачивания списка покупок."""

        user = request.user
        counting_dict = {}
        for recipe in user.shopping_cart.all():
            for ingredient in recipe.ingredients.all():
                recipe_ingredient_obj = get_object_or_404(
                    RecipeIngredients,
                    recipe_id=recipe.id,
                    ingredient_id=ingredient.id
                )
                name = ingredient.name
                amount = recipe_ingredient_obj.amount
                measurement_unit = ingredient.measurement_unit
                if name in counting_dict:
                    counting_dict[name]['amount'] += amount
                else:
                    counting_dict[name] = {
                        'amount': amount,
                        'measurement_unit': measurement_unit
                    }
        shopping_cart_text = '\n'.join(
            f'{name} - {data["amount"]} {data["measurement_unit"]}.'
            for name, data in counting_dict.items()
        )
        response = HttpResponse(shopping_cart_text, content_type='text/plain')
        response['Content-Disposition'] = 'attachment; filename="cart.pdf"'
        return response

    @action(detail=True, methods=['post'])
    def add_to_favorite(self, request, pk=None):
        """Метод для добавления рецепта в избранное."""
        recipe = self.get_object()
        user = request.user
        user.favorites.add(recipe)
        serializer = ShortRecipeSerializer(recipe)
        return Response(serializer.data, status=status.HTTP_200_OK)

    @action(detail=True, methods=['delete'])
    def remove_from_favorite(self, request, pk=None):
        """Метод для удаления рецепта из избранного."""
        recipe = self.get_object()
        user = request.user
        user.favorites.remove(recipe)
        return Response(
            {'message': 'Рецепт удален из списка избранного'},
            status=status.HTTP_200_OK)


class IngredientsViewSet(viewsets.ModelViewSet):
    """Вьюсет для обработки запросов к ингредиентам."""

    queryset = Ingredients.objects.all()
    serializer_class = IngredientsSerializer
    permission_classes = (AllowAny,)
    http_method_names = ('get',)
    pagination_class = PageNumberPagination
    filter_backends = (SearchFilter, OrderingFilter)
    search_fields = ('name',)
    ordering_fields = ('name',)


class TagsViewSet(viewsets.ModelViewSet):
    """Вьюсет для обработки запросов к тегам."""

    queryset = Tags.objects.all()
    serializer_class = TagsSerializer
    permission_classes = (AllowAny,)
    filter_backends = (SearchFilter, OrderingFilter)
    search_fields = ('name',)
    ordering_fields = ('slug',)
    http_method_names = ('get',)
