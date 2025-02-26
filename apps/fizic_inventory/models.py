import string
import random
from django.db import models
from apps.inventory.models import Box, Section

def generate_code():
    """Generează un cod unic de 7 caractere (litere și cifre)."""
    characters = string.ascii_letters + string.digits
    return ''.join(random.choices(characters, k=7))

# Opțiuni pentru culoare
COLOR_CHOICES = [
    ('red', 'Red'),
    ('blue', 'Blue'),
    ('green', 'Green'),
    ('simple', 'Simple'),
]

# Opțiuni pentru simbol – X înseamnă „none”
SYMBOL_CHOICES = [
    ('A', 'A'),
    ('K', 'K'),
    ('O', 'O'),
    ('X', 'X (None)'),
]

# Statusul containerelor fizice
CONTAINER_STATUS_CHOICES = [
    ('free', 'Free'),
    ('assigned', 'Assigned'),
    ('in_process', 'In Process'),
    ('returned', 'Returned'),
    ('sold', 'Sold'),
]

# Tipurile de zonă (folosim numele simplu: type)
ZONE_TYPE_CHOICES = [
    ('depozit', 'Depozit'),
    ('receptie', 'Recepție'),
    ('livrare', 'Livrare'),
    ('procesare', 'Procesare'),
    ('unknown', 'Unknown'),
]

class Zone(models.Model):
    code = models.CharField(
        max_length=7,
        unique=True,
        default=generate_code,
        editable=False,
        help_text="Cod unic de 7 caractere generat automat."
    )
    name = models.CharField(max_length=100)
    type = models.CharField(max_length=20, choices=ZONE_TYPE_CHOICES, default='depozit')
    capacity = models.PositiveIntegerField(help_text="Capacitatea totală a zonei.")
    current_occupancy = models.PositiveIntegerField(default=0, help_text="Numărul actual de containere.")

    def __str__(self):
        return f"{self.code} - {self.name} ({self.get_type_display()})"

    def update_occupancy(self):
        self.current_occupancy = self.containers.count()
        self.save()

    def clear_zone(self):
        """
        Resetează toate containerele din această zonă:
        pentru fiecare container se apelează metoda reset (setând statusul la free și eliminând box-ul).
        """
        for container in self.containers.all():
            container.reset()
        self.update_occupancy()


class Container(models.Model):
    code = models.CharField(
        max_length=7,
        unique=True,
        default=generate_code,
        help_text="Cod unic de 7 caractere; se generează automat dacă nu este specificat."
    )
    color = models.CharField(max_length=10, choices=COLOR_CHOICES)
    symbol = models.CharField(max_length=1, choices=SYMBOL_CHOICES, default='X')
    zone = models.ForeignKey(
        Zone,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='containers',
        help_text="Zona în care se află containerul."
    )
    box = models.ForeignKey(
        Box,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        help_text="Box-ul asociat (din apps.inventory); doar unul la un moment dat."
    )
    status = models.CharField(max_length=20, choices=CONTAINER_STATUS_CHOICES, default='free')
    virtual_box_code = models.CharField(
        max_length=50,
        blank=True,
        null=True,
        help_text="Codul cutiei virtuale asociate, dacă există."
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Container {self.code} ({self.get_status_display()})"

    def move_to_zone(self, new_zone):
        old_zone = self.zone
        self.zone = new_zone
        self.save()
        if old_zone:
            old_zone.update_occupancy()
        if new_zone:
            new_zone.update_occupancy()
        ContainerEvent.objects.create(
            container=self,
            event_type='moved',
            from_zone=old_zone,
            to_zone=new_zone,
            notes=f"Moved from {old_zone} to {new_zone}" if old_zone and new_zone else "Moved"
        )

    def reset(self):
        """
        Resetează containerul: setează statusul la free, elimină box-ul asociat,
        și înregistrează un eveniment de check-in (validare retur).
        """
        previous_status = self.status
        if self.box:
            self.box = None
        self.status = 'free'
        self.save()
        ContainerEvent.objects.create(
            container=self,
            event_type='checkin',
            notes=f"Container reset from status {previous_status} to free."
        )

    def add_virtual_box(self, virtual_code):
        self.virtual_box_code = virtual_code
        self.save()
        ContainerEvent.objects.create(
            container=self,
            event_type='assigned',
            notes=f"Virtual box code {virtual_code} added."
        )

    @classmethod
    def add_box(cls, code, color, symbol):
        """
        Dacă un container cu codul dat există deja, acesta este marcat ca returned
        (eliminând box-ul) și se înregistrează evenimentul; altfel se creează un container nou.
        """
        try:
            container = cls.objects.get(code=code)
            container.status = 'returned'
            container.box = None
            container.save()
            ContainerEvent.objects.create(
                container=container,
                event_type='checkin',
                notes="Existing container marked as returned via add_box."
            )
            return container, "updated"
        except cls.DoesNotExist:
            container = cls.objects.create(code=code, color=color, symbol=symbol, status='free')
            ContainerEvent.objects.create(
                container=container,
                event_type='assigned',
                notes="New container created via add_box."
            )
            return container, "created"

    @classmethod
    def check_box(cls, code):
        """
        Returnează containerul cu codul dat (sau None dacă nu există).
        """
        try:
            return cls.objects.get(code=code)
        except cls.DoesNotExist:
            return None


class ContainerEvent(models.Model):
    EVENT_TYPE_CHOICES = [
        ('moved', 'Moved'),
        ('assigned', 'Assigned'),
        ('returned', 'Returned'),
        ('sold', 'Sold'),
        ('delivered', 'Delivered'),
        ('checkin', 'Check-in'),
    ]
    container = models.ForeignKey(
        Container,
        on_delete=models.CASCADE,
        related_name='events'
    )
    event_type = models.CharField(max_length=20, choices=EVENT_TYPE_CHOICES)
    event_date = models.DateTimeField(auto_now_add=True)
    from_zone = models.ForeignKey(
        Zone,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='events_from',
        help_text="Zona de unde a fost mutat, dacă este cazul."
    )
    to_zone = models.ForeignKey(
        Zone,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='events_to',
        help_text="Zona în care a fost mutat, dacă este cazul."
    )
    box = models.ForeignKey(
        Box,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        help_text="Box-ul asociat evenimentului."
    )
    notes = models.TextField(blank=True, null=True)

    def __str__(self):
        return f"Container {self.container.code} - {self.get_event_type_display()} at {self.event_date}"
