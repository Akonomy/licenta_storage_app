from django.urls import path
from . import views

urlpatterns = [
    path('', views.product_list, name='product_list'),
    path('box/<int:box_id>/', views.product_detail, name='product_detail'),
    path('add-to-cart/<int:box_id>/', views.add_to_cart, name='add_to_cart'),
    path('cart/', views.cart_view, name='cart'),
    path('checkout/', views.checkout, name='checkout'),
    path('remove-from-cart/<int:box_id>/', views.remove_from_cart, name='remove_from_cart'),
    
]
