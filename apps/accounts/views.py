# apps/accounts/views.py

from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login, logout, get_user_model
from django.contrib.auth.decorators import login_required
from django.contrib import messages

User = get_user_model()

@login_required
def manage_users_view(request):
    # Asigurăm accesul doar pentru utilizatorii master sau superuser
    if not (request.user.is_master or request.user.is_superuser):
        messages.error(request, 'Acces interzis. Nu aveți permisiunea necesară.')
        return redirect('profile')

    # Căutare: se poate căuta după username, email, prenume sau nume
    query = request.GET.get('q', '')
    if query:
        users = User.objects.filter(
            Q(username__icontains=query) |
            Q(email__icontains=query) |
            Q(first_name__icontains=query) |
            Q(last_name__icontains=query)
        )
    else:
        users = User.objects.all()

    # Procesăm modificarea rolului unui utilizator
    if request.method == "POST":
        user_id = request.POST.get('user_id')
        new_role = request.POST.get('role')
        try:
            user_to_update = User.objects.get(pk=user_id)
            if new_role in dict(User.ROLE_CHOICES):
                user_to_update.role = new_role
                user_to_update.save()
                messages.success(request, f"Rolul pentru utilizatorul {user_to_update.username} a fost actualizat.")
            else:
                messages.error(request, "Rol invalid selectat.")
        except User.DoesNotExist:
            messages.error(request, "Utilizatorul nu a fost găsit.")
        return redirect('manage_users')

    context = {
        'users': users,
        'query': query,
        'ROLE_CHOICES': User.ROLE_CHOICES,
    }
    return render(request, 'accounts/manage_users.html', context)




def login_view(request):
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        user = authenticate(request, username=username, password=password)
        if user:
            login(request, user)
            messages.success(request, 'Te-ai conectat cu succes.')
            return redirect('profile')
        else:
            messages.error(request, 'Username sau parolă incorecte.')
    return render(request, 'accounts/login.html')

def register_view(request):
    if request.method == 'POST':
        username  = request.POST.get('username')
        email     = request.POST.get('email')
        password1 = request.POST.get('password1')
        password2 = request.POST.get('password2')
        
        if password1 != password2:
            messages.error(request, 'Parolele nu se potrivesc.')
            return render(request, 'accounts/register.html')
        
        if User.objects.filter(username=username).exists():
            messages.error(request, 'Username-ul este deja folosit.')
            return render(request, 'accounts/register.html')
        
        # Creăm un nou utilizator
        user = User.objects.create_user(username=username, email=email, password=password1)
        messages.success(request, 'Contul a fost creat cu succes. Te rog conectează-te.')
        return redirect('login')
        
    return render(request, 'accounts/register.html')

@login_required
def logout_view(request):
    logout(request)
    messages.success(request, 'Te-ai deconectat cu succes.')
    return redirect('login')

@login_required
def profile_view(request):
    # Afișează profilul utilizatorului
    return render(request, 'accounts/profile.html', {'user': request.user})

@login_required
def edit_account_view(request):
    user = request.user
    if request.method == 'POST':
        username   = request.POST.get('username')
        email      = request.POST.get('email')
        first_name = request.POST.get('first_name')
        last_name  = request.POST.get('last_name')
        
        # Verificăm dacă username-ul este deja folosit de alt utilizator
        if User.objects.filter(username=username).exclude(pk=user.pk).exists():
            messages.error(request, 'Username-ul este deja folosit de alt utilizator.')
            return render(request, 'accounts/edit_account.html', {'user': user})
        
        user.username   = username
        user.email      = email
        user.first_name = first_name
        user.last_name  = last_name
        user.save()
        messages.success(request, 'Contul a fost actualizat cu succes.')
        return redirect('profile')
    
    return render(request, 'accounts/edit_account.html', {'user': user})

@login_required
def delete_account_view(request):
    if request.method == 'POST':
        request.user.delete()
        messages.success(request, 'Contul tău a fost șters.')
        return redirect('register')
    return render(request, 'accounts/delete_account.html')
