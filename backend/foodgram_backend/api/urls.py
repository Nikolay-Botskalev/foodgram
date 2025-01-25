"""Эндпоинты."""

from django.urls import include, path
from rest_framework.routers import DefaultRouter

from api.views import (
    IngredientsViewSet,
    FollowingView,
    LoginView,
    LogoutView,
    MeUserView,
    MeUserAvatarView,
    MeUserFollowingView,
    ReciepesViewSet,
    SetPasswordView,
    short_link_redirect,
    TagsViewSet,
    UserViewSet,
)


app_name = 'api'

router = DefaultRouter()

router.register(r'recipes', ReciepesViewSet)
router.register(r'ingredients', IngredientsViewSet)
router.register(r'tags', TagsViewSet)
router.register(r'users', UserViewSet, basename='users')

urlpatterns = [
    path('auth/token/login/', LoginView.as_view(), name='login'),

    path('auth/token/logout/', LogoutView.as_view(), name='logout'),

    path('users/me/', MeUserView.as_view(), name='me_user'),

    path('users/me/avatar/', MeUserAvatarView.as_view(), name='me_avatar'),

    path('users/set_password/', SetPasswordView.as_view(), name='set_pass'),

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
         name='cart'),

    path('recipes/<int:pk>/favorite/', ReciepesViewSet.as_view(
        {'post': 'add_to_favorite', 'delete': 'remove_from_favorite'}),
        name='favorite'),

    path('', include(router.urls)),

    path('<str:string>', short_link_redirect, name='short_link_redirect')
]
