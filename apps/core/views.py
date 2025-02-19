from django.shortcuts import render

# core/views.py
from django.http import HttpResponse

from django.shortcuts import render

def home(request):
    links = [
        {"url": "/account/login/", "name": "Login"},
        {"url": "/account/register/", "name": "Register"},
        {"url": "/account/", "name": "Profile"},
        {"url": "/account/manage-users/", "name": "Administrare Utilizatori"},
        # Adaugă alte linkuri după necesități
    ]
    return render(request, "core/home.html", {"links": links})
