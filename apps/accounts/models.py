# apps/accounts/models.py

from django.contrib.auth.models import AbstractUser
from django.db import models

class CustomUser(AbstractUser):
    is_master = models.BooleanField(default=False)  # True pentru utilizatorii master
    ROLE_CHOICES = (
        ('common', 'Common'),
        ('robot', 'Robot'),
        ('admin', 'Admin'),
    )
    # Pentru utilizatorii obișnuiți, se setează un rol; pentru master, acest câmp poate fi lăsat nul
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, blank=True, null=True)
    
    def has_page_access(self, page_permission):
        """
        Metodă simplificată pentru verificarea accesului la pagini.
        Utilizatorul master are acces la toate paginile.
        Pentru utilizatorii obișnuiți, se verifică dacă rolul corespunde cu permisiunea necesară.
        """
        if self.is_master:
            return True
        return self.role == page_permission
