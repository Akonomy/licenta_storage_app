# store_new/urls.py
from django.urls import path
from . import views

app_name = 'store_new'

urlpatterns = [
    # Lista de produse (grid, 12 pe pagină)
    path('', views.product_list, name='product_list'),




   
    path('search/', views.box_search, name='box_search'),



    # Detalii produs (clic pe imagine sau titlu)
    path('product/<int:product_id>/', views.product_detail, name='product_detail'),

    # Adaugă produs în coș
    path('add-to-cart/<int:product_id>/', views.add_to_cart, name='add_to_cart'),

    # Vizualizare coș
    path('cart/', views.cart_view, name='cart_view'),

    # Actualizare coș (modificare cantitate)
    path('update-cart/', views.update_cart, name='update_cart'),

    # Eliminare produs din coș
    path('remove-from-cart/<int:product_id>/', views.remove_from_cart, name='remove_from_cart'),

    # Checkout și plasare comandă
    path('checkout/', views.checkout, name='checkout'),

    # Detalii comandă
    path('order/<int:order_id>/', views.order_detail, name='order_detail'),

    path('orderhistory/', views.order_history, name='order_history'),

    # Anulare comandă (doar dacă statusul este 'pending' sau 'waiting')
    path('order/<int:order_id>/cancel/', views.cancel_order, name='cancel_order'),

    # Actualizare element din comandă (modificare cantitate din comanda plasată)
    path('order/<int:order_id>/update-item/<int:item_id>/', views.update_order_item, name='update_order_item'),

    # Adăugare manuală de produse (numai pentru admin sau utilizatori master)
    path('add-product/', views.add_product, name='add_product'),













     path('<str:box_code>/', views.box_detail, name='box_detail'),


   






]
