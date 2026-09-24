from django.urls import path
from rest_framework import routers

from .views.auth_view import AuthView
from .views.user_view import UserView

router = routers.DefaultRouter()
router.register('auth', AuthView, basename='auth')
router.register('user', UserView, basename='user')

urlpatterns = [
    path('auth/google/', AuthView.as_view({'post': 'google'}), name='auth-google'),
] + router.urls
