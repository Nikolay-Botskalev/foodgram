"""Эндпоинты."""

from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import (
    IngredientsViewSet,
    FollowingView,
    GetTokenView,
    MeUserView,
    MeUserAvatarView,
    MeUserFollowingView,
    ReciepesViewSet,
    SetPasswordView,
    SignUpViewSet,
    TagsViewSet,
    UserViewSet,
)


app_name = 'api'

router = DefaultRouter()

# Запросы к рецептам (список, создание, получение, обновление, удаление)
router.register(r'recipes', ReciepesViewSet)
router.register(r'ingredients', IngredientsViewSet)  # Запросы к ингредиентам
router.register(r'tags', TagsViewSet)  # Запросы к тегам
router.register(r'auth/signup', SignUpViewSet)
router.register(r'users', UserViewSet, basename='admin_users')

urlpatterns = [
    path('auth/', include('djoser.urls')),

    path('auth/', include('djoser.urls.jwt')),

    path('auth/token/login/', GetTokenView.as_view()),

    path('users/me/', MeUserView.as_view(), name='me_user'),

    path('users/me/avatar/', MeUserAvatarView.as_view(), name='me_avatar'),

    path('users/set_password/', SetPasswordView.as_view(), name='setpasword'),

    path('users/subscriptions/',
         MeUserFollowingView.as_view(),
         name='me_user_following'),

    path('users/<int:pk>/subscribe/',
         FollowingView.as_view(),
         name='following'),

    path('recipes/<int:pk>/get-link/', ReciepesViewSet.as_view(
        {'get': 'get_link'}), name='get_link'),

    path('recipes/download_shopping_cart/', ReciepesViewSet.as_view(
        {'get': 'download_shopping_cart'}), name='download_shopping_cart_all'),

    path('recipes/<int:pk>/shopping_cart/', ReciepesViewSet.as_view(
        {'post': 'add_to_shopping_cart',
         'delete': 'remove_from_shopping_cart'}),
         name='download_shopping_cart'),

    path('recipes/<int:pk>/favorite/', ReciepesViewSet.as_view(
        {'post': 'add_to_favorite', 'delete': 'remove_from_favorite'}),
        name='favorite'),

    path('', include(router.urls)),
]
