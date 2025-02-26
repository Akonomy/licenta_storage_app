from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required, user_passes_test
from .models import Task, RobotStatus
from .forms import TaskForm
from django.http import JsonResponse
from django.contrib import messages

from rest_framework.decorators import api_view, authentication_classes, permission_classes
from rest_framework.permissions import IsAuthenticated

# Folosește clasa de autentificare personalizată definită în apps.accounts
from apps.accounts.authentication import CustomJWTAuthentication

from apps.store_new.models import Order, OrderItem, Product, BoxQueue, DeliveryQueue


from apps.inventory.models import Box, Section

# Web interface views (rămân neschimbate)
def inventory_home(request):
    return render(request, 'robot_interface/robot_interface_home.html')

@login_required
@user_passes_test(lambda u: u.has_page_access('robot'))
def task_queue(request):
    tasks = Task.objects.filter(status='pending').order_by('created_at')
    return render(request, 'robot_interface/task_queue.html', {'tasks': tasks})

@login_required
@user_passes_test(lambda u: u.has_page_access('robot'))
def robot_messages(request):
    status = RobotStatus.objects.last()
    return render(request, 'robot_interface/robot_messages.html', {'status': status})

@login_required
@user_passes_test(lambda u: u.has_page_access('robot'))
def control_panel(request):
    if request.method == 'POST':
        form = TaskForm(request.POST)
        if form.is_valid():
            task = form.save(commit=False)
            task.created_by = request.user
            task.save()
            return redirect('task_queue')
    else:
        form = TaskForm()
    return render(request, 'robot_interface/control_panel.html', {'form': form})

# API views folosind autentificarea personalizată

@api_view(['GET'])
@authentication_classes([CustomJWTAuthentication])
@permission_classes([IsAuthenticated])
def fetch_tasks_api(request):
    tasks = Task.objects.filter(status='pending').order_by('created_at')
    tasks_data = []
    for task in tasks:
        task_data = {
            'id': task.id,
            'task_type': task.task_type,
            'box_code': task.box.code if task.box else None,
            'custom_action': task.custom_action,
        }
        if task.source_section:
            task_data['source_section'] = {
                'name': task.source_section.nume_custom,
                'type': task.source_section.tip_sectie,
            }
        else:
            task_data['source_section'] = None

        if task.target_section:
            task_data['target_section'] = {
                'name': task.target_section.nume_custom,
                'type': task.target_section.tip_sectie,
            }
        else:
            task_data['target_section'] = None

        tasks_data.append(task_data)
    return JsonResponse({'tasks': tasks_data})

@api_view(['POST'])
@authentication_classes([CustomJWTAuthentication])
@permission_classes([IsAuthenticated])
def update_task_status_api(request, task_id):
    try:
        task = Task.objects.get(id=task_id)
        status = request.data.get('status')
        reason = request.data.get('reason', '')

        if status not in dict(Task.TASK_STATUS_CHOICES):
            return JsonResponse({'error': 'Invalid status'}, status=400)

        task.status = status
        if reason:
            task.reason = reason
        task.save()

        if status == 'completed':
            if task.task_type == 'move_box' and task.box and task.source_section and task.target_section:
                task.source_section.move_box(task.box, task.target_section)
            elif task.task_type == 'add_box' and task.box and task.target_section:
                task.target_section.add_box(task.box)
            elif task.task_type == 'remove_box' and task.box and task.source_section:
                task.box.remove_from_section()

        return JsonResponse({'message': 'Task status updated'})
    except Task.DoesNotExist:
        return JsonResponse({'error': 'Task not found'}, status=404)

@api_view(['POST'])
@authentication_classes([CustomJWTAuthentication])
@permission_classes([IsAuthenticated])
def update_robot_status_api(request):
    status = request.data.get('status')
    message = request.data.get('message', '')

    if status not in dict(RobotStatus.STATUS_CHOICES):
        return JsonResponse({'error': 'Invalid status'}, status=400)

    robot_status, created = RobotStatus.objects.get_or_create(id=1)
    robot_status.status = status
    robot_status.message = message
    robot_status.save()

    return JsonResponse({'message': 'Robot status updated'})

@api_view(['GET'])
@authentication_classes([CustomJWTAuthentication])
@permission_classes([IsAuthenticated])
def get_box_details_api(request, box_code):
    from apps.inventory.models import Box  # Import model Box din aplicația inventory
    try:
        box = Box.objects.get(code=box_code)
        box_data = {
            'code': box.code,
            'name': box.name,
            'color': box.color,
            'price': box.price,
            'section': {
                'name': box.section.nume_custom,
                'type': box.section.tip_sectie,
            }
        }
        return JsonResponse({'box': box_data})
    except Box.DoesNotExist:
        return JsonResponse({'error': 'Box not found'}, status=404)







# Funcții helper pentru re-verificarea cozilor
def recheck_box_queue():
    """
    Parcurge fiecare element din BoxQueue și încearcă alocarea unei cutii.
    Dacă se găsește o cutie liberă, actualizează comanda, schimbă statusul cutiei
    și, ulterior, verifică dacă se poate aloca și zona de livrare. În funcție de aceasta,
    fie se creează un task pentru mutarea cutiei, fie se adaugă în DeliveryQueue.
    """
    # Se caută toate intrările din coada de cutii
    for queue_item in BoxQueue.objects.all().order_by('created_at'):
        order = queue_item.order
        # Verificăm dacă comanda este încă în așteptare și nu are cutie alocată
        if order.waiting and order.package_box is None:
            free_box = Box.objects.filter(section__tip_sectie='depozit', status='in_stoc').first()
            if free_box:
                # Alocăm cutia pentru comandă
                order.package_box = free_box
                free_box.status = 'sold'
                free_box.save()
                # Eliminăm intrarea din coada de cutii
                queue_item.delete()
                # Determinăm codul regiunii și căutăm zona de livrare
                region_code = order.get_delivery_region_code()
                delivery_section = None
                if region_code in [1, 2, 3]:
                    delivery_section = Section.objects.filter(tip_sectie='livrare', nume_custom__icontains='1').first()
                    if not delivery_section:
                        delivery_section = Section.objects.filter(tip_sectie='livrare', nume_custom__icontains='2').first()
                else:
                    delivery_section = Section.objects.filter(tip_sectie='livrare', nume_custom__icontains='4').first()
                    if not delivery_section:
                        delivery_section = Section.objects.filter(tip_sectie='livrare', nume_custom__icontains='5').first()
                
                if delivery_section:
                    # Dacă se găsește zona, se creează task-ul de mutare a cutiei
                    Task.objects.create(
                        task_type='move_box',
                        box=free_box,
                        source_section=free_box.section,
                        target_section=delivery_section,
                        status='pending',
                        created_by=order.user
                    )
                    # Actualizăm comanda
                    order.status = 'livrare'
                    order.waiting = False
                else:
                    # Dacă nu se găsește zona, adăugăm comanda în coada de livrare
                    order.status = 'procesare'
                    order.waiting = True
                    DeliveryQueue.objects.create(
                        order=order,
                        box=free_box,
                        region_code=region_code
                    )
                order.save()

def recheck_delivery_queue():
    """
    Parcurge fiecare element din DeliveryQueue și încearcă alocarea unei zone de livrare.
    Dacă se găsește o zonă disponibilă, se creează task-ul de mutare a cutiei către acea zonă
    și se actualizează comanda, apoi se elimină elementul din coada de livrare.
    """
    for delivery_item in DeliveryQueue.objects.all().order_by('created_at'):
        order = delivery_item.order
        free_box = order.package_box  # Ar trebui să existe deja din etapa de cutii
        if free_box:
            region_code = order.get_delivery_region_code()
            delivery_section = None
            if region_code in [1, 2, 3]:
                delivery_section = Section.objects.filter(tip_sectie='livrare', nume_custom__icontains='1').first()
                if not delivery_section:
                    delivery_section = Section.objects.filter(tip_sectie='livrare', nume_custom__icontains='2').first()
            else:
                delivery_section = Section.objects.filter(tip_sectie='livrare', nume_custom__icontains='4').first()
                if not delivery_section:
                    delivery_section = Section.objects.filter(tip_sectie='livrare', nume_custom__icontains='5').first()
            
            if delivery_section:
                # Creează task pentru mutarea cutiei
                Task.objects.create(
                    task_type='move_box',
                    box=free_box,
                    source_section=free_box.section,
                    target_section=delivery_section,
                    status='pending',
                    created_by=order.user
                )
                # Actualizează comanda
                order.status = 'livrare'
                order.waiting = False
                order.save()
                # Șterge elementul din coada de livrare
                delivery_item.delete()

# =====================================================
# Web view pentru gestionarea cozilor cu acțiune "update"
# =====================================================
@login_required
@user_passes_test(lambda u: u.has_page_access('robot'))
def queue_management(request):
    """
    Această view permite vizualizarea și modificarea cozilor:
     - "BoxQueue" pentru comenzi care așteaptă alocarea unei cutii
     - "DeliveryQueue" pentru comenzi care așteaptă o zonă de livrare
    Pe lângă posibilitatea de ștergere a elementelor,
    se poate declanșa o acțiune "update" care re-verifică disponibilitatea și alocă automat resursele.
    """
    if request.method == 'POST':
        action = request.POST.get('action')
        if action == 'delete':
            item_type = request.POST.get('item_type')  # 'box' sau 'delivery'
            item_id = request.POST.get('item_id')
            if item_id:
                if item_type == 'box':
                    try:
                        item = BoxQueue.objects.get(id=item_id)
                        item.delete()
                    except BoxQueue.DoesNotExist:
                        messages.error(request, 'Elementul din BoxQueue nu a fost găsit.')
                elif item_type == 'delivery':
                    try:
                        item = DeliveryQueue.objects.get(id=item_id)
                        item.delete()
                    except DeliveryQueue.DoesNotExist:
                        messages.error(request, 'Elementul din DeliveryQueue nu a fost găsit.')
        elif action == 'update':
            # Se declanșează re-verificarea pentru ambele cozi
            recheck_box_queue()
            recheck_delivery_queue()
            messages.success(request, 'Cozile au fost actualizate în funcție de disponibilitate.')

        return redirect('queue_management')  # Denumirea rutei din urls.py

    # Pentru metoda GET, se extrag elementele din cele două cozi
    box_queue_items = BoxQueue.objects.all().order_by('created_at')
    delivery_queue_items = DeliveryQueue.objects.all().order_by('created_at')
    context = {
        'box_queue': box_queue_items,
        'delivery_queue': delivery_queue_items,
    }
    return render(request, 'robot_interface/queue_management.html', context)

# =====================================================
# API views pentru BoxQueue și DeliveryQueue
# =====================================================

@api_view(['GET'])
@authentication_classes([CustomJWTAuthentication])
@permission_classes([IsAuthenticated])
def fetch_box_queue_api(request):
    """
    Returnează o listă de elemente din BoxQueue.
    """
    box_queue = BoxQueue.objects.all().order_by('created_at')
    data = []
    for item in box_queue:
        data.append({
            'id': item.id,
            'order_id': item.order.id,
            'created_at': item.created_at,
        })
    return JsonResponse({'box_queue': data})

@api_view(['GET'])
@authentication_classes([CustomJWTAuthentication])
@permission_classes([IsAuthenticated])
def fetch_delivery_queue_api(request):
    """
    Returnează o listă de elemente din DeliveryQueue.
    """
    delivery_queue = DeliveryQueue.objects.all().order_by('created_at')
    data = []
    for item in delivery_queue:
        data.append({
            'id': item.id,
            'order_id': item.order.id,
            'box_id': item.box.id,
            'region_code': item.region_code,
            'created_at': item.created_at,
        })
    return JsonResponse({'delivery_queue': data})

@api_view(['POST'])
@authentication_classes([CustomJWTAuthentication])
@permission_classes([IsAuthenticated])
def update_queue_item_api(request):
    """
    Permite efectuarea unor modificări asupra unui element din oricare dintre cozi.
    Exemplu:
      - 'delete' pentru ștergerea unui element
      - 'update' pentru re-verificarea și alocarea resurselor
    Parametrii așteptați în request (format JSON):
      - item_type: 'box' sau 'delivery' (doar pentru acțiunea 'delete')
      - action: 'delete' sau 'update'
      - item_id: id-ul elementului (necesar doar pentru 'delete')
    """
    action = request.data.get('action')
    if action == 'delete':
        item_type = request.data.get('item_type')
        item_id = request.data.get('item_id')
        if not all([item_type, item_id]):
            return JsonResponse({'error': 'Parametri lipsă'}, status=400)
        if item_type == 'box':
            try:
                item = BoxQueue.objects.get(id=item_id)
                item.delete()
                return JsonResponse({'message': 'Elementul din BoxQueue a fost șters'})
            except BoxQueue.DoesNotExist:
                return JsonResponse({'error': 'Elementul din BoxQueue nu a fost găsit'}, status=404)
        elif item_type == 'delivery':
            try:
                item = DeliveryQueue.objects.get(id=item_id)
                item.delete()
                return JsonResponse({'message': 'Elementul din DeliveryQueue a fost șters'})
            except DeliveryQueue.DoesNotExist:
                return JsonResponse({'error': 'Elementul din DeliveryQueue nu a fost găsit'}, status=404)
        else:
            return JsonResponse({'error': 'Tip de element invalid'}, status=400)
    elif action == 'update':
        # Re-verifică ambele cozi
        recheck_box_queue()
        recheck_delivery_queue()
        return JsonResponse({'message': 'Cozile au fost actualizate'}, status=200)
    else:
        return JsonResponse({'error': 'Acțiune invalidă'}, status=400)








# Noua API view pentru logout (revocare token)
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework_simplejwt.tokens import RefreshToken
from apps.accounts.models import RevokedToken  # Import modelul din apps.accounts

class CustomLogoutView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        refresh_token = request.data.get("refresh")
        if not refresh_token:
            return Response({"error": "Token lipsă"}, status=400)
        try:
            token = RefreshToken(refresh_token)  # Validare opțională
            RevokedToken.objects.create(token=refresh_token)
            return Response({"message": "Logout reușit"}, status=200)
        except Exception as e:
            return Response({"error": "Token invalid sau eroare"}, status=400)
