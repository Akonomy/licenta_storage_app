# apps/accounts/views.py

from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.contrib.auth import get_user_model

User = get_user_model()

def login_view(request):
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        user = authenticate(request, username=username, password=password)
        if user:
            login(request, user)
            messages.success(request, 'Te-ai conectat cu succes.')
            # Redirecționează spre o pagină de start sau profil (ajustează după necesități)
            return redirect('home')
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
        
        # Creează un nou utilizator
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
def delete_account_view(request):
    if request.method == 'POST':
        user = request.user
        user.delete()
        messages.success(request, 'Contul tău a fost șters.')
        return redirect('register')
    return render(request, 'accounts/delete_account.html')
