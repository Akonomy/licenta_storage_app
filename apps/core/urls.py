# core/urls.py
from django.urls import path
from . import views

urlpatterns = [
    path('', views.home, name='home'),
    # adaugă și alte rute dacă este necesar
]
