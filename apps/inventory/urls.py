from django.urls import path
from . import views

urlpatterns = [
    # Home
    path('', views.inventory_home, name='inventory_home'),

    # Cutiile (Box)
    path('boxes/', views.box_list, name='box_list'),
    path('add-box/', views.add_box, name='add_box'),
    path('edit-box/<int:box_id>/', views.edit_box, name='edit_box'),
    path('delete-box/<int:box_id>/', views.delete_box, name='delete_box'),

    # Secțiunile (Section)
    path('sections/', views.section_list, name='section_list'),
    path('add-section/', views.add_section, name='add_section'),
    path('edit-section/<int:section_id>/', views.edit_section, name='edit_section'),
    path('delete-section/<int:section_id>/', views.delete_section, name='delete_section'),
    path('export/', views.export_data, name='export_data'),
    path('import/', views.import_data, name='import_data'),
]
