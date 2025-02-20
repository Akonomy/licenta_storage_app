from django.urls import path
from .views import start_game, game_detail, game_over, game_won

from django.urls import path
from . import views

urlpatterns = [
    path('', views.start_game, name='start_game'),
    path('start/', views.start_game, name='start_game'),
    path('game/<int:game_id>/', views.game_detail, name='game_detail'),
    path('game/<int:game_id>/won/', views.game_won, name='game_won'),  # New URL for the win page
    path('game/<int:game_id>/over/', views.game_over, name='game_over'),
]
