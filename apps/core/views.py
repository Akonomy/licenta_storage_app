from django.shortcuts import render

# core/views.py
from django.http import HttpResponse

def home(request):
    return HttpResponse("Bine ai venit la aplicația principală!")
