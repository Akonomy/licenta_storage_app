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
        # Dacă este master sau superuser, acordă acces complet
        if self.is_master or self.is_superuser:
            return True
        return self.role == page_permission







class RevokedToken(models.Model):
    token = models.CharField(max_length=500, unique=True)
    revoked_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.token