import random
import string
import requests
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages

from django.contrib.auth.decorators import login_required, user_passes_test
# MODELE SPECIFICE (local): Order, OrderItem, Product
from .models import Order, OrderItem, Product

# MODELE EXTERNE – INVENTAR: Box, Section
from apps.inventory.models import Box, Section

# MODELE EXTERNE – ROBOT INTERFACE: Task
from apps.robot_interface.models import Task

# Alte modele externe (din apps.store_new)
from apps.store_new.models import DeliveryQueue  # importăm modelul nou

API_PRODUCTS_URL = "https://api.escuelajs.co/api/v1/products"


#-------------CODE1: Views folosind doar modelele specifice (.models: Order, OrderItem, Product) -------------
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
#-------------END CODE1-------------


#-------------CODE2: Views care folosesc modelele din apps.inventory.models (Box, Section) -------------
@login_required
def order_detail(request, order_id):
    """
    Această view preia detaliile unei comenzi și folosește modelul Box (din apps.inventory.models)
    prin atributul package_box al comenzii.
    """
    order = get_object_or_404(Order, id=order_id, user=request.user)
    items = order.orderitem_set.all()
    # Obținem cutia asociată cu comanda, dacă există
    box = order.package_box  
    return render(request, 'store_new/order_detail.html', {'order': order, 'items': items, 'box': box})

def box_search(request):
    """
    View pentru căutarea unei cutii/container după cod.
    Dacă se introduce un cod de 6 caractere, se caută o cutie (Box);
    dacă se introduce un cod de 7 caractere, se caută un container din fizic_inventory.
    """
    if request.method == 'POST':
        code = request.POST.get('box_id')
        if not code:
            messages.error(request, "Te rog introdu un cod valid.")
            return redirect('store_new:box_search')
        # Redirecționăm către view-ul de detaliere, folosind parametrul 'box_code'
        return redirect('store_new:box_detail', box_code=code)
    return render(request, 'store_new/box_search.html')


def box_detail(request, box_code):
    """
    View pentru afișarea detaliilor.
    
    - Dacă 'box_code' are 6 caractere:
      Caută și afișează detaliile unei cutii (Box) din apps.inventory.models,
      inclusiv istoricul comenzilor în care a fost alocată cutia.
      
    - Dacă 'box_code' are 7 caractere:
      Caută un container (din apps.fizic_inventory.models) și afișează informații detaliate:
        * Datele containerului
        * Evenimentele containerului
        * Datele cutiei asociate (dacă există)
        * Comenzile care au folosit acea cutie (dacă există)
    """
    if len(box_code) == 6:
        # Tratare pentru codul de cutie (Box) – afişare standard
        box = get_object_or_404(Box, code=box_code)
        order_history = Order.objects.filter(package_box=box)
        context = {
            'box': box,
            'order_history': order_history,
        }
        return render(request, 'store_new/box_detail.html', context)
    elif len(box_code) == 7:
        # Tratare pentru codul containerului din fizic_inventory
        from apps.fizic_inventory.models import Container
        container = get_object_or_404(Container, code=box_code)
        container_events = container.events.all()
        # Dacă containerul are asociată o cutie, se caută și comenzile aferente
        box = container.box
        orders = Order.objects.filter(package_box=box) if box else None
        context = {
            'container': container,
            'container_events': container_events,
            'box': box,
            'orders': orders,
        }
        return render(request, 'store_new/container_detail.html', context)
    else:
        messages.error(request, "Codul introdus nu este valid.")
        return redirect('store_new:box_search')


@login_required
def checkout(request):
    """
    View pentru plasarea unei comenzi.
    Această funcție utilizează:
      - Modelele locale (Order, OrderItem) pentru crearea comenzii și elementelor de comandă.
      - Modelele din apps.inventory.models (Box, Section) pentru alocarea unui pachet.
      - Modelele din apps.fizic_inventory.models (Container, Zone) pentru asocierea containerului.
      - Modelul Task din apps.robot_interface.models pentru crearea unui task de mutare a containerului.
      - Modelul DeliveryQueue din apps.store_new.models pentru gestionarea cozii de așteptare.
    """

    #----------BLOCK 1: Verificări inițiale ----------
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
    #----------END BLOCK 1----------

    if request.method == 'POST':
        #----------BLOCK 2: Extracția datelor din formular ----------
        county = request.POST.get('county')
        street = request.POST.get('street')
        commune = request.POST.get('commune', '')
        #----------END BLOCK 2----------

        #----------BLOCK 3: Crearea inițială a comenzii ----------
        order = Order.objects.create(
            user=user,
            total_amount=total,
            county=county,
            street=street,
            commune=commune,
            status='confirmare',  # inițial: în curs de confirmare
            waiting=True
        )
        region_code = order.get_delivery_region_code()
        #----------END BLOCK 3----------

        #----------BLOCK 4: Alocarea unui pachet pentru comandă ----------
        free_box = Box.objects.filter(section__tip_sectie='depozit', status='in_stoc').first()
        if not free_box:
            from apps.store_new.models import BoxQueue  # import local pentru BoxQueue
            BoxQueue.objects.create(order=order)
            messages.info(request, 'Nu există pachete libere disponibile. Comanda este în coada de așteptare pentru alocarea unui pachet.')
        else:
            order.package_box = free_box
            free_box.status = 'sold'
            free_box.save()
        #----------END BLOCK 4----------

        #----------BLOCK 5: Asocierea containerului și crearea task-ului ----------
        if free_box:
            # Importăm Container și Zone din apps.fizic_inventory.models
            from apps.fizic_inventory.models import Container, Zone

            # Stabilim litera dorită: prima literă din numele pachetului (dacă există)
            desired_letter = free_box.name[0].upper() if free_box.name else None

            # Căutăm un container cu aceeași culoare (și, opțional, cu aceeași literă)
            container_qs = Container.objects.filter(
                status='free',
                box__isnull=True,
                color=free_box.color
            )
            if desired_letter:
                container = container_qs.filter(symbol=desired_letter).first()
            else:
                container = container_qs.first()

            # Dacă nu s-a găsit, urmăm prioritățile: simple, red, green, blue
            if not container:
                for priority_color in ['simple', 'red', 'green', 'blue']:
                    container = Container.objects.filter(
                        status='free',
                        box__isnull=True,
                        color=priority_color
                    ).first()
                    if container:
                        break

            if container:
                # Asociem containerul cu pachetul și actualizăm statusul acestuia
                container.box = free_box
                container.status = 'assigned'
                container.save()

                # Determinăm zona țintă de livrare pe baza regiunii
                target_zone = None
                if region_code in [1, 2, 3]:
                    target_zone = Zone.objects.filter(name__icontains='Livrare_1', type='livrare').first()
                    if not target_zone:
                        target_zone = Zone.objects.filter(name__icontains='Livrare_2', type='livrare').first()
                else:
                    target_zone = Zone.objects.filter(name__icontains='Livrare_2', type='livrare').first()
                    if not target_zone:
                        target_zone = Zone.objects.filter(name__icontains='Livrare_3', type='livrare').first()

                # Dacă nu se găsește nicio zonă conform preferințelor, alegem totuși Livrare_1 sau Livrare_2
                if not target_zone:
                    target_zone = Zone.objects.filter(name__icontains='Livrare_1', type='livrare').first() or \
                                  Zone.objects.filter(name__icontains='Livrare_2', type='livrare').first()

                # Creăm un task pentru mutarea containerului (nu a pachetului)
                Task.objects.create(
                    task_type='move_box',  # task pentru container
                    box=container,  # câmpul "box" din Task se referă acum la container
                    source_section=container.zone,  # zona curentă a containerului
                    target_section=target_zone,  # zona țintă determinată
                    status='pending',
                    created_by=user
                )

                order.status = 'livrare'
                order.waiting = False
            else:
                # Dacă nu se găsește un container potrivit, se adaugă comanda în coada de așteptare pentru asocierea containerului
                from apps.store_new.models import DeliveryQueue  # import local pentru DeliveryQueue
                DeliveryQueue.objects.create(
                    order=order,
                    box=free_box,
                    region_code=region_code
                )
                messages.info(request, 'Nu a fost găsit un container potrivit. Comanda este în coada de așteptare pentru asocierea containerului.')
            order.save()
        #----------END BLOCK 5----------

        #----------BLOCK 6: Crearea elementelor comenzii și actualizarea contului utilizatorului ----------
        for pid, item in cart.items():
            OrderItem.objects.create(
                order=order,
                product_title=item['title'],
                product_price=item['price'],
                quantity=item['quantity'],
                external_id=int(pid) if item.get('external') else None
            )
        order.calculate_total()
        user.coins -= total
        user.save()
        #----------END BLOCK 6----------

        #----------BLOCK 7: Finalizarea procesului de comandă ----------
        request.session['cart'] = {}
        messages.success(request, 'Comanda a fost plasată. Vei primi actualizări privind stadiul comenzii.')
        return redirect('store_new:order_detail', order_id=order.id)
        #----------END BLOCK 7----------

    #----------BLOCK 8: Renderizarea paginii de checkout pentru cererile GET ----------
    total = sum(int(item['price']) * item['quantity'] for item in cart.values())
    return render(request, 'store_new/checkout.html', {'total': total})
    #----------END BLOCK 8----------






import random
import string


from .models import WithdrawalCoinCode

def generate_random_code_3():
    """Generează un cod de 3 caractere (majuscule și cifre)."""
    return ''.join(random.choices(string.ascii_uppercase + string.digits, k=3))

@login_required
@user_passes_test(lambda u: u.has_page_access('admin'))
def generate_withdrawal_code(request):
    """
    Pagina de generare a unui cod de withdraw.
    Administratorul poate introduce numărul de utilizări (uses), valoarea coins per utilizare,
    și valoarea maximă ce se poate extrage (max_withdrawal).
    Total_amount se calculează ca: (uses * coins_per_use) + 1.
    """
    generated_code = None
    if request.method == 'POST':
        uses = request.POST.get('uses')
        coins_per_use = request.POST.get('coins_per_use')
        max_withdrawal = request.POST.get('max_withdrawal')
        try:
            uses = int(uses)
            coins_per_use = int(coins_per_use)
            max_withdrawal = int(max_withdrawal)
        except (ValueError, TypeError):
            messages.error(request, "Valorile trebuie să fie numere.")
            return redirect('store_new:generate_withdrawal_code')
        
        total_amount = uses * coins_per_use + 1  # plus 1 pentru a fi sigur că totalul > withdrawal
        # Generăm un cod unic
        while True:
            code = generate_random_code_3()
            if not WithdrawalCoinCode.objects.filter(code=code).exists():
                break

        coin_code = WithdrawalCoinCode.objects.create(code=code, total_amount=total_amount, max_withdrawal=max_withdrawal)
        generated_code = coin_code.code
        messages.success(request, f"Cod generat: {generated_code}. Total amount: {total_amount}, Max withdrawal: {max_withdrawal}")
    context = {
        'generated_code': generated_code,
    }
    return render(request, 'store_new/generate_withdrawal_code.html', context)

@login_required
def redeem_withdrawal_code(request):
    """
    Pagina pentru redeem codul de withdraw.
    Utilizatorul introduce codul; dacă acesta este valid, se extrage suma:
      - Dacă total_amount >= max_withdrawal: se extrage max_withdrawal.
      - Dacă total_amount < max_withdrawal: se extrage tot ce rămâne, codul expiră și se șterge.
    """
    if request.method == 'POST':
        input_code = request.POST.get('code', '').strip().upper()
        coin_code = WithdrawalCoinCode.objects.filter(code=input_code).first()
        if not coin_code:
            messages.error(request, "Cod invalid.")
            return redirect('store_new:redeem_withdrawal_code')
        extracted, expired_msg = coin_code.redeem(request.user)
        if expired_msg:
            messages.info(request, expired_msg)
        messages.success(request, f"Ai primit {extracted} coins!")
        return redirect('store_new:cart_view')
    return render(request, 'store_new/redeem_withdrawal_code.html')
