from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required, user_passes_test
from .models import Task, RobotStatus
from .forms import TaskForm
from django.http import JsonResponse

from rest_framework.decorators import api_view, authentication_classes, permission_classes
from rest_framework.permissions import IsAuthenticated

# Folosește clasa de autentificare personalizată definită în apps.accounts
from apps.accounts.authentication import CustomJWTAuthentication

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
                'name': task.source_section.name,
                'type': task.source_section.type,
            }
        else:
            task_data['source_section'] = None

        if task.target_section:
            task_data['target_section'] = {
                'name': task.target_section.name,
                'type': task.target_section.type,
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
    from inventory.models import Box  # Import model Box din aplicația inventory
    try:
        box = Box.objects.get(code=box_code)
        box_data = {
            'code': box.code,
            'name': box.name,
            'color': box.color,
            'price': box.price,
            'section': {
                'name': box.section.name,
                'type': box.section.type,
            }
        }
        return JsonResponse({'box': box_data})
    except Box.DoesNotExist:
        return JsonResponse({'error': 'Box not found'}, status=404)

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
