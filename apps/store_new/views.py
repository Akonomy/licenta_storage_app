import random
import requests
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from .models import Order, OrderItem, Product
from apps.inventory.models import Box, Section
from apps.robot_interface.models import Task
from apps.store_new.models import DeliveryQueue  # importăm modelul nou




API_PRODUCTS_URL = "https://api.escuelajs.co/api/v1/products"

def fetch_api_products(page=1, limit=12):
    offset = (page - 1) * limit
    params = {'offset': offset, 'limit': limit}
    try:
        response = requests.get(API_PRODUCTS_URL, params=params, timeout=5)
        if response.status_code == 200:
            return response.json()
    except Exception as e:
        print("Eroare API:", e)
    return None

def product_list(request):
    page = int(request.GET.get('page', 1))
    limit = int(request.GET.get('limit', 12))
    products = fetch_api_products(page, limit)
    if products is not None:
        for p in products:
            if 'images' in p and p['images']:
                p['main_image'] = p['images'][0]
    else:
        # Fallback: folosim produsele adăugate manual
        products = list(Product.objects.all().values())
    context = {
        'products': products,
        'page': page,
        'limit': limit,
        'next_page': page + 1,
        'prev_page': page - 1 if page > 1 else None,
    }
    return render(request, 'store_new/product_list.html', context)

def product_detail(request, product_id):
    try:
        response = requests.get(f"{API_PRODUCTS_URL}/{product_id}", timeout=5)
        if response.status_code == 200:
            product = response.json()
            if 'images' in product and product['images']:
                product['main_image'] = product['images'][0]
        else:
            product = None
    except Exception:
        product = None

    if product is None:
        product_obj = get_object_or_404(Product, id=product_id)
        product = {
            'title': product_obj.title,
            'price': product_obj.price,
            'description': product_obj.description,
            'main_image': product_obj.main_image,
            'secondary_images': product_obj.secondary_images,
        }
    return render(request, 'store_new/product_detail.html', {'product': product})

def add_to_cart(request, product_id):
    cart = request.session.get('cart', {})
    product = None
    try:
        response = requests.get(f"{API_PRODUCTS_URL}/{product_id}", timeout=5)
        if response.status_code == 200:
            product = response.json()
    except Exception:
        pass

    if product is None:
        product_obj = get_object_or_404(Product, id=product_id)
        product = {
            'title': product_obj.title,
            'price': product_obj.price,
        }
    
    if str(product_id) not in cart:
        cart[str(product_id)] = {
            'title': product.get('title') or '',
            'price': product.get('price'),
            'quantity': 1,
            'external': True if product.get('id') is not None else False,
        }
        messages.success(request, 'Produs adăugat în coș.')
    else:
        cart[str(product_id)]['quantity'] += 1
        messages.info(request, 'Cantitatea produsului a fost actualizată.')
    request.session['cart'] = cart
    return redirect('store_new:cart_view')

def cart_view(request):
    cart = request.session.get('cart', {})
    cart_items = []
    total = 0
    for pid, item in cart.items():
        try:
            price = int(item['price'])
        except (ValueError, TypeError):
            price = 0
        total += price * item['quantity']
        cart_items.append({
            'id': pid,
            'title': item['title'],
            'price': item['price'],
            'quantity': item['quantity'],
        })
    context = {
        'cart_items': cart_items,
        'total': total,
    }
    return render(request, 'store_new/cart.html', context)

@login_required
def update_cart(request):
    """
    Permite actualizarea cantității produselor din coș sau eliminarea acestora
    (dacă cantitatea devine 0).
    Se așteaptă ca input-urile din formular să aibă numele de forma 'quantity_<product_id>'.
    """
    if request.method == 'POST':
        cart = request.session.get('cart', {})
        for key, value in request.POST.items():
            if key.startswith('quantity_'):
                product_id = key.split('_')[1]
                try:
                    new_quantity = int(value)
                    if new_quantity > 0:
                        cart[product_id]['quantity'] = new_quantity
                    else:
                        cart.pop(product_id, None)
                except ValueError:
                    continue
        request.session['cart'] = cart
        messages.success(request, 'Coșul a fost actualizat.')
    return redirect('store_new:cart_view')

@login_required
def remove_from_cart(request, product_id):
    cart = request.session.get('cart', {})
    product_key = str(product_id)  # conversie la string
    if product_key in cart:
        del cart[product_key]
        messages.success(request, 'Produsul a fost eliminat din coș.')
    request.session['cart'] = cart
    return redirect('store_new:cart_view')



@login_required
def checkout(request):
    cart = request.session.get('cart', {})
    if not cart:
        messages.error(request, 'Coșul este gol.')
        return redirect('store_new:product_list')

    total = sum(int(item['price']) * item['quantity'] for item in cart.values())
    if total < 100:
        messages.error(request, 'Comanda trebuie să fie de cel puțin 100 lei.')
        return redirect('store_new:cart_view')

    user = request.user
    if user.coins < total:
        messages.error(request, 'Nu ai suficiente monede. Joacă jocurile din apps.games pentru a câștiga mai multe.')
        return redirect('games:start_game')

    if request.method == 'POST':
        county = request.POST.get('county')
        street = request.POST.get('street')
        commune = request.POST.get('commune', '')

        # 1. Creăm comanda cu status inițial "confirmare" (in curs de confirmare)
        order = Order.objects.create(
            user=user,
            total_amount=total,
            county=county,
            street=street,
            commune=commune,
            status='confirmare',  # noul status ce indică "în curs de confirmare"
            waiting=True
        )

        # Determinăm codul regiunii pentru livrare
        region_code = order.get_delivery_region_code()

        # 2. Căutăm o cutie liberă în secțiunea de depozit
        free_box = Box.objects.filter(section__tip_sectie='depozit', status='in_stoc').first()


        if not free_box:
            # Nu există cutii disponibile: creăm o intrare în coada de așteptare pentru cutii
            from apps.store_new.models import BoxQueue  # import local pentru modelul BoxQueue
            BoxQueue.objects.create(order=order)
            messages.info(request, 'Nu există cutii libere disponibile. Comanda este în coada de așteptare pentru alocarea unei cutii.')
        else:
            # Alocăm cutia pentru comandă
            order.package_box = free_box
            free_box.status = 'sold'

            # 3. Căutăm zona de livrare conform regiunii
            delivery_section = None
            if region_code in [1, 2, 3]:
                # Pentru regiunile 1, 2 și 3, căutăm secțiunea ce conține mai întâi '1'
                delivery_section = Section.objects.filter(tip_sectie='livrare', nume_custom__icontains='1').first()
                if not delivery_section:
                    # Dacă nu e găsită, încercăm cu '2'
                    delivery_section = Section.objects.filter(tip_sectie='livrare', nume_custom__icontains='2').first()
            else:
                # Pentru restul regiunilor, căutăm secțiunea ce conține '4' și apoi '5'
                delivery_section = Section.objects.filter(tip_sectie='livrare', nume_custom__icontains='4').first()
                if not delivery_section:
                    delivery_section = Section.objects.filter(tip_sectie='livrare', nume_custom__icontains='5').first()

            if delivery_section:
                # Dacă s-a găsit o zonă de livrare, se creează un task de mutare a cutiei
                Task.objects.create(
                    task_type='move_box',
                    box=free_box,
                    source_section=free_box.section,
                    target_section=delivery_section,
                    status='pending',
                    created_by=user
                )
                # Actualizăm statusul și secțiunea cutiei
                
                free_box.status = 'sold'
                free_box.save()

                # Actualizăm comanda: statusul devine "livrare" (în curs de livrare)
                order.status = 'livrare'
                order.waiting = False
            else:
                # Dacă nu s-a găsit nicio zonă de livrare liberă, comanda trece la stadiul "procesare"
                # (adică, a fost găsită cutia, dar nu zona de livrare)
                order.status = 'procesare'
                order.waiting = True

                # Salvăm detalii minime pentru a gestiona ulterior coada de livrare
                DeliveryQueue.objects.create(
                    order=order,
                    box=free_box,
                    region_code=region_code
                )
                messages.info(request, 'Nu a fost găsită o zonă de livrare liberă. Comanda este în coada de așteptare pentru alocarea unei zone de livrare.')
            order.save()

            # 4. Creăm elementele comenzii
            for pid, item in cart.items():
                OrderItem.objects.create(
                    order=order,
                    product_title=item['title'],
                    product_price=item['price'],
                    quantity=item['quantity'],
                    external_id=int(pid) if item.get('external') else None
                )
            order.calculate_total()

            # 5. Deducem monedele din contul utilizatorului
            user.coins -= total
            user.save()

        request.session['cart'] = {}
        messages.success(request, 'Comanda a fost plasată. Vei primi actualizări privind stadiul comenzii.')
        return redirect('store_new:order_detail', order_id=order.id)

    total = sum(int(item['price']) * item['quantity'] for item in cart.values())
    return render(request, 'store_new/checkout.html', {'total': total})

@login_required
def order_detail(request, order_id):
    order = get_object_or_404(Order, id=order_id, user=request.user)
    items = order.orderitem_set.all()
    # Obținem cutia asociată cu comanda, dacă există
    box = order.package_box  
    return render(request, 'store_new/order_detail.html', {'order': order, 'items': items, 'box': box})


@login_required
def order_history(request):
    # Obținem toate comenzile utilizatorului, ordonate descrescător după dată
    orders = Order.objects.filter(user=request.user).order_by('-ordered_date')
    return render(request, 'store_new/order_history.html', {'orders': orders})


@login_required
def cancel_order(request, order_id):
    """
    Permite anularea unei comenzi dacă aceasta este încă în stadiile 'pending' sau 'waiting'.
    """
    order = get_object_or_404(Order, id=order_id, user=request.user)
    if order.status in ['pending', 'waiting']:
        order.status = 'canceled'
        order.save()
        messages.success(request, 'Comanda a fost anulată.')
    else:
        messages.error(request, 'Comanda nu poate fi anulată în acest stadiu.')
    return redirect('store_new:order_detail', order_id=order.id)

@login_required
def update_order_item(request, order_id, item_id):
    """
    Permite actualizarea cantității unui produs dintr-o comandă dacă aceasta nu a fost finalizată.
    Dacă noua cantitate este 0, produsul este eliminat din comandă.
    """
    order = get_object_or_404(Order, id=order_id, user=request.user)
    if order.status not in ['pending', 'waiting']:
        messages.error(request, 'Nu se pot modifica produsele din această comandă.')
        return redirect('store_new:order_detail', order_id=order.id)
    order_item = get_object_or_404(OrderItem, id=item_id, order=order)
    if request.method == 'POST':
        try:
            new_quantity = int(request.POST.get('quantity', order_item.quantity))
            if new_quantity > 0:
                order_item.quantity = new_quantity
                order_item.save()
                messages.success(request, 'Cantitatea a fost actualizată.')
            else:
                order_item.delete()
                messages.success(request, 'Produsul a fost eliminat din comandă.')
            order.calculate_total()
        except ValueError:
            messages.error(request, 'Cantitate invalidă.')
    return redirect('store_new:order_detail', order_id=order.id)

# Vizualizare pentru adăugarea manuală de produse (doar pentru admin sau utilizatori master)
@login_required
def add_product(request):
    if not (request.user.is_staff or request.user.is_superuser or getattr(request.user, 'is_master', False)):
        messages.error(request, 'Nu ai permisiunea de a adăuga produse.')
        return redirect('store_new:product_list')
    
    if request.method == 'POST':
        title = request.POST.get('title')
        price = request.POST.get('price')
        description = request.POST.get('description', '')
        main_image = request.POST.get('main_image')
        secondary_images_str = request.POST.get('secondary_images', '')
        secondary_images = [url.strip() for url in secondary_images_str.split(',') if url.strip()]
        product = Product(title=title, price=price, description=description, main_image=main_image, secondary_images=secondary_images)
        try:
            product.full_clean()
            product.save()
            messages.success(request, 'Produsul a fost adăugat cu succes.')
            return redirect('store_new:product_detail', product_id=product.id)
        except Exception as e:
            messages.error(request, f"Eroare: {e}")
    return render(request, 'store_new/add_product.html')


def box_search(request):
    if request.method == 'POST':
        box_code = request.POST.get('box_id')
        if not box_code:
            messages.error(request, "Te rog introdu un cod de cutie valid.")
            return redirect('store_new:box_search')
        # Redirecționăm către view-ul de detaliere, folosind parametrul 'box_code'
        return redirect('store_new:box_detail', box_code=box_code)
    return render(request, 'store_new/box_search.html')


def box_detail(request, box_code):
    # Căutăm cutia după cod (nu după id)
    box = get_object_or_404(Box, code=box_code)
    # Obținem istoricul comenzilor în care cutia a fost alocată
    order_history = Order.objects.filter(package_box=box)
    
    context = {
        'box': box,
        'order_history': order_history,
    }
    return render(request, 'store_new/box_detail.html', context)