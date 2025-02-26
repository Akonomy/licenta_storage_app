from django.urls import path
from . import views

app_name = "fizic_inventory"

urlpatterns = [
    # Home page
    path('', views.home, name='home'),

    # Container URLs (rutele statice sunt listate mai întâi)
    path('containers/', views.container_list, name='container_list'),
    path('container/add/', views.add_box_view, name='add_box'),
    path('container/check/', views.check_box_view, name='check_box'),
    path('container/reset_defaults/', views.reset_container_defaults_view, name='reset_container_defaults'),
    path('container/<str:code>/reset/', views.reset_container_view, name='reset_container'),
    path('container/<str:code>/edit/', views.edit_container_view, name='edit_container'),
    path('container/<str:code>/add_virtual/', views.add_virtual_box_view, name='add_virtual_box'),
    path('container/<str:code>/move/', views.move_container, name='move_container'),
    path('container/<str:code>/', views.container_detail, name='container_detail'),

    # Zone URLs (rutele statice sunt listate mai întâi)
    path('zones/', views.zone_list, name='zone_list'),
    path('zone/add/', views.add_zone_view, name='add_zone'),
    path('zone/reset_defaults/', views.reset_zone_defaults_view, name='reset_zone_defaults'),
    path('zone/<str:code>/edit/', views.edit_zone_view, name='edit_zone'),
    path('zone/<str:code>/clear/', views.clear_zone_view, name='clear_zone'),
    path('zone/<str:code>/', views.zone_detail, name='zone_detail'),
]
