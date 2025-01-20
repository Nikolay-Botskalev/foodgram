"""Вьюсеты."""

from django.conf import settings
from django.contrib.auth import authenticate
from django.http import HttpResponse
from django.shortcuts import get_object_or_404
from rest_framework import generics, status, viewsets
from rest_framework.authtoken.models import Token
from rest_framework.decorators import action
from rest_framework.filters import OrderingFilter, SearchFilter
from rest_framework.pagination import PageNumberPagination
from rest_framework.permissions import (
    AllowAny, IsAuthenticated, IsAuthenticatedOrReadOnly)
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.viewsets import ModelViewSet

from recipes.models import (
    Ingredients, MyUser, RecipeIngredients, Recipes, Tags)
from api.permissions import IsAuthorOrReadOnly
from api.serializers import (
    AvatarSerializer,
    IngredientsSerializer,
    LoginSerializer,
    RecipeSerializer,
    SetPasswordSerializer,
    ShortRecipeSerializer,
    SubscribedUserSerializer,
    TagsSerializer,
    UserSerializer,
)


class SetPasswordView(APIView):
    """ViewSet для смены пароля пользователем."""

    permission_classes = (IsAuthenticated,)

    def post(self, request):
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
            {'message': 'Пароль успешно изменен'}, status=status.HTTP_200_OK)


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

        token, created = Token.objects.get_or_create(user=user)

        if not created:
            return Response({'error': 'Ошибка при создании токена.'},
                            status=status.HTTP_400_BAD_REQUEST,)
        return Response({
            'auth_token': token.key
        })


class LogoutView(APIView):
    """Удаление токена."""

    permission_classes = (IsAuthenticated,)

    def post(self, request):
        """Завершение сессии пользователя."""

        user = request.user
        Token.objects.filter(user=user).delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class UserViewSet(ModelViewSet):
    """View для запросов к пользователям."""

    queryset = MyUser.objects.all()
    serializer_class = UserSerializer
    permission_classes = (AllowAny,)
    pagination_class = PageNumberPagination
    filter_backends = (SearchFilter, OrderingFilter)
    search_fields = ('recipes__tags__slug', 'username',)
    ordering_fields = ('username',)
    http_method_names = ('get', 'post', 'put', 'delete')

    def create(self, request, *args, **kwargs):
        """Создание пользователя."""
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        headers = self.get_success_headers(serializer.data)
        return Response(
            serializer.data, status=status.HTTP_201_CREATED, headers=headers)

    @action(detail=True, methods=['get'])
    def recipes(self, request, pk=None):
        """Получение списка рецептов пользователя."""
        user = self.get_object()
        queryset = Recipes.objects.filter(author=user).order_by('-pub_date')
        queryset = self.filter_queryset(queryset)
        serializer = ShortRecipeSerializer(queryset, many=True)
        return Response(serializer.data)

    def perform_create(self, serializer):
        user = serializer.save()
        user.set_password(serializer.validated_data['password'])
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
    search_fields = ('tags__slug', 'name',)
    ordering_fields = ('id',)
    http_method_names = ('get', 'post', 'patch', 'delete')

    def perform_create(self, serializer):
        serializer.save(author=self.request.user)

    def perform_update(self, serializer):
        instance = serializer.save()
        return instance

    def get_permissions(self):
        if self.action == 'get_link' or self.action == 'get':
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
        recipe = self.get_object()
        user = request.user
        user.shopping_cart.add(recipe)
        return Response(
            {'message': f'Рецепт {recipe.name!r} добавлен в список покупок'},
            status=status.HTTP_201_CREATED)

    @action(detail=True, methods=['delete'])
    def remove_from_shopping_cart(self, request, pk=None):
        """Метод для удаления рецепта из списка покупок."""
        recipe = self.get_object()
        user = request.user
        user.shopping_cart.remove(recipe)
        return Response(
            {'message': f'Рецепт {recipe.name!r} успешно удален из покупок'},
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
            f"{name.capitalize()} - {data['amount']}\
 {data['measurement_unit']}."
            for name, data in counting_dict.items())
        response = HttpResponse(shopping_cart_text, content_type='text/plain')
        response['Content-Disposition'] = 'attachment; filename="cart.pdf"'
        return response

    @action(detail=False, methods=['get'])
    def favorites(self, request):
        """Метод для получения списка избранного."""
        user = self.request.user
        queryset = user.favorites.all()
        queryset = self.filter_queryset(queryset)
        serializer = ShortRecipeSerializer(queryset, many=True)
        return Response(serializer.data)

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
            {'message': f'Рецепт {recipe.name!r} удален из списка избранного'},
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
