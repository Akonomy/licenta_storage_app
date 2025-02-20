import random
import requests
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from .models import Order, OrderItem, Product
from apps.inventory.models import Box, Section
from apps.robot_interface.models import Task

API_PRODUCTS_URL = "https://api.escuelajs.co/api/v1/products"

def fetch_api_products(page=1, limit=10):
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
    limit = int(request.GET.get('limit', 10))
    products = fetch_api_products(page, limit)
    if products is not None:
        for p in products:
            if 'images' in p and p['images']:
                p['main_image'] = p['images'][0]
    else:
        # Dacă API-ul nu răspunde, folosim produsele adăugate manual
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
    # Încearcă să preia produsul din API; dacă nu, din baza de date locală
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
    
    # Construim dicționarul pentru coș folosind metoda .get() (fără fallback pe atribute)
    if str(product_id) not in cart:
        cart[str(product_id)] = {
            'title': product.get('title') or '',
            'price': product.get('price'),
            'quantity': 1,
            # Dacă cheia 'id' există în dicționar, considerăm produsul venit din API
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

        # Determină zona de livrare pe baza județului (exemplu simplificat)
        delivery_section = None
        if county in ['Bucuresti', 'Ilfov']:
            delivery_section = Section.objects.filter(tip_sectie='livrare', nume_custom__icontains='București').first()
        elif county in ['Cluj', 'Sibiu', 'Brasov']:
            delivery_section = Section.objects.filter(tip_sectie='livrare', nume_custom__icontains='Transilvania').first()
        else:
            delivery_section = Section.objects.filter(tip_sectie='livrare').first()

        # Caută o cutie liberă în secțiunea depozit
        free_box = Box.objects.filter(section__tip_sectie='depozit', status='in_stoc').first()

        order = Order.objects.create(
            user=user,
            total_amount=total,
            county=county,
            street=street,
            commune=commune,
            status='processing' if free_box else 'pending',
            waiting=False if free_box else True
        )

        # Creează elementele comenzii
        for pid, item in cart.items():
            OrderItem.objects.create(
                order=order,
                product_title=item['title'],
                product_price=item['price'],
                quantity=item['quantity'],
                external_id=int(pid) if item.get('external') else None
            )
        order.calculate_total()

        # Deducem monedele din contul utilizatorului
        user.coins -= total
        user.save()

        if free_box:
            order.package_box = free_box
            order.save()
            if delivery_section:
                # Creăm un task pentru mutarea cutiei din depozit în zona de livrare
                Task.objects.create(
                    task_type='move_box',
                    box=free_box,
                    source_section=free_box.section,
                    target_section=delivery_section,
                    status='pending',
                    created_by=user
                )
                # Actualizăm statusul și secțiunea cutiei
                free_box.section = delivery_section
                free_box.status = 'sold'
                free_box.save()
            else:
                order.waiting = True
                order.save()
                messages.info(request, 'Nu a fost găsită o zonă de livrare liberă. Comanda este în așteptare.')
        else:
            messages.info(request, 'Nu există cutii libere disponibile. Comanda va fi procesată când devine disponibilă o cutie.')
        
        request.session['cart'] = {}
        messages.success(request, 'Comanda a fost plasată.')
        return redirect('store_new:order_detail', order_id=order.id)

    return render(request, 'store_new/checkout.html', {'total': total})

@login_required
def order_detail(request, order_id):
    order = get_object_or_404(Order, id=order_id, user=request.user)
    items = order.orderitem_set.all()
    return render(request, 'store_new/order_detail.html', {'order': order, 'items': items})

# Vizualizare pentru adăugarea manuală de produse (numai pentru admin sau utilizatori master)
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
        # Pentru câmpul secondary_images se poate prelua o listă de URL-uri, de exemplu, separate prin virgulă
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
