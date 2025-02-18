# apps/accounts/urls.py
# apps/accounts/urls.py

from django.urls import path
from .views import (
    login_view, register_view, logout_view, profile_view,
    edit_account_view, delete_account_view
)

urlpatterns = [
    path('login/', login_view, name='login'),
    path('register/', register_view, name='register'),
    path('logout/', logout_view, name='logout'),
    path('delete/', delete_account_view, name='delete_account'),
    path('edit/', edit_account_view, name='edit_account'),
    path('', profile_view, name='profile'),  # Ruta default: /accounts/ afișează profilul
]
