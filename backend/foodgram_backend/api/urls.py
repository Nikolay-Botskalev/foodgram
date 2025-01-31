"""Эндпоинты."""

from django.urls import include, path
from rest_framework.routers import DefaultRouter

from api.views import (IngredientsViewSet, LoginView, LogoutView,
                       ReciepesViewSet, TagsViewSet,
                       UserViewSet, short_link_redirect)

app_name = 'api'

router = DefaultRouter()

router.register('recipes', ReciepesViewSet, basename='recipes')
router.register('ingredients', IngredientsViewSet, basename='ingredients')
router.register('tags', TagsViewSet, basename='tags')
router.register('users', UserViewSet, basename='users')

urlpatterns = [
    path('auth/token/login/', LoginView.as_view(), name='login'),

    path('auth/token/logout/', LogoutView.as_view(), name='logout'),

    path('', include(router.urls)),

    path('<str:string>', short_link_redirect, name='short_link_redirect')
]
