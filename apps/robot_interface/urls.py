
# robot_interface/urls.py

from django.urls import path
from . import views
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView

urlpatterns = [
    # Web interface views
    path('', views.inventory_home, name='robot_interface_home'),
    path('tasks/', views.task_queue, name='task_queue'),
    path('messages/', views.robot_messages, name='robot_messages'),
    path('control/', views.control_panel, name='control_panel'),

    path('queue_management/', views.queue_management,name='queue_management'),


]

# API endpoints
urlpatterns += [
    path('api/tasks/', views.fetch_tasks_api, name='fetch_tasks_api'),
    path('api/task/first/', fetch_first_task_api, name='fetch_first_task_api'),
    path('api/tasks/<int:task_id>/update/', views.update_task_status_api, name='update_task_status_api'),
    path('api/robot_status/update/', views.update_robot_status_api, name='update_robot_status_api'),
    path('api/boxes/<str:box_code>/', views.get_box_details_api, name='get_box_details_api'),

    path('api/fetch_box_queue_api', views.fetch_box_queue_api, name='fetch_box_queue_api'),



    path('api/container/add/', views.add_container_api, name='add_container_api'),
    path('api/container/<str:container_code>/modify/', views.modify_container_api, name='modify_container_api'),
    path('api/container/<str:container_code>/check/', views.check_container_api, name='check_container_api'),
    path('api/container/<str:container_code>/reset/', views.reset_container_api, name='reset_container_api'),
    path('api/container/<str:container_code>/change-zone/', views.change_container_zone_api, name='change_container_zone_api'),





    # JWT authentication endpoints
    path('api/token/', TokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('api/token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
]
  