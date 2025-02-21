
from django.shortcuts import render, get_object_or_404, redirect
from apps.inventory.models import Box, Section
from django.contrib.auth.decorators import login_required
from django.contrib import messages  # For flash messages

from .models import Order, OrderItem
from apps.robot_interface.models import Task  # Import Task model








def product_list(request):
    boxes = Box.objects.filter(section__tip_sectie='depozit')
    return render(request, 'store/product_list.html', {'boxes': boxes})


def product_detail(request, box_code):
    box = get_object_or_404(Box, code=box_code)
    return render(request, 'store/product_detail.html', {'box': box})


def add_to_cart(request, box_id):
    box = get_object_or_404(Box, id=box_id)
    cart = request.session.get('cart', {})

    # Check if the box is in 'depozit' before adding
    if box.section.tip_sectie != 'depozit':
        messages.error(request, 'This item is no longer available.')
        return redirect('product_list')

    if str(box_id) not in cart:
        cart[str(box_id)] = {'price': str(box.price)}
        request.session['cart'] = cart
        messages.success(request, 'Item added to cart.')
    else:
        messages.info(request, 'Item is already in your cart.')

    return redirect('cart')


def cart_view(request):
    cart = request.session.get('cart', {})
    cart_items = []
    total_price = 0

    updated_cart = cart.copy()  # To remove items that are no longer in 'depozit'

    for box_id, item in cart.items():
        box = Box.objects.get(id=box_id)

        # Check if the box is still in 'depozit'
        if box.section.tip_sectie != 'depozit':
            # Remove it from cart
            del updated_cart[box_id]
            messages.error(request, f'Item {box.code} is no longer available and has been removed from your cart.')
            continue

        price = float(item['price'])
        total_price += price

        cart_items.append({
            'box': box,
            'price': price,
        })

    # Update the cart in session if needed
    if updated_cart != cart:
        request.session['cart'] = updated_cart

    return render(request, 'store/cart.html', {'cart_items': cart_items, 'total_price': total_price})




@login_required
def checkout(request):
    cart = request.session.get('cart', {})
    if not cart:
        messages.error(request, 'Your cart is empty.')
        return redirect('product_list')

    invalid_boxes = []
    valid_boxes = []

    for box_id in cart.keys():
        box = Box.objects.get(id=box_id)
        # Check if box is still in 'depozit'
        if box.section.tip_sectie != 'depozit':
            invalid_boxes.append(box)
        else:
            valid_boxes.append(box)

    if invalid_boxes:
        # Remove invalid boxes from cart
        for box in invalid_boxes:
            del cart[str(box.id)]
        request.session['cart'] = cart
        messages.error(request, 'Some items are no longer available and have been removed from your cart.')
        return redirect('cart')

    if request.method == 'POST':
        # Calculate total price
        total_price = sum(box.price for box in valid_boxes)

        # Check if user has enough coins
        user = request.user
        if user.coins < total_price:
            messages.error(
                request,
                'You do not have enough coins to complete this order. '
                'Please play games to earn more coins.'
            )
            return redirect('cart')

        # Deduct coins from user
        user.coins -= total_price
        user.save()

        # Process the order
        order = Order.objects.create(user=request.user, is_ordered=True)
        for box in valid_boxes:
            OrderItem.objects.create(order=order, box=box)

            # Ensure 'livrare' section exists
            livrare_section, created = Section.objects.get_or_create( nume_custom='livrare', defaults={'tip_sectie': 'livrare', 'max_capacity': 1000}
)

            # Create a Task to move the box to 'livrare'
            Task.objects.create(
                task_type='move_box',
                box=box,
                source_section=box.section,
                target_section=livrare_section,
                status='pending',
                created_by=user  # Assuming Task model has a 'created_by' field
            )

            # Move box to 'livrare' in the database (mark as sold)
            box.section = livrare_section
            box.save()

        # Clear the cart
        request.session['cart'] = {}
        return render(request, 'store/order_complete.html', {'order': order})

    else:
        # Display checkout page
        return render(request, 'store/checkout.html')



def remove_from_cart(request, box_id):
    cart = request.session.get('cart', {})
    if str(box_id) in cart:
        del cart[str(box_id)]
        request.session['cart'] = cart
        messages.success(request, 'Item removed from cart.')
    else:
        messages.error(request, 'Item not found in cart.')
    return redirect('cart')



