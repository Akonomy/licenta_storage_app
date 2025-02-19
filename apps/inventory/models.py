# apps/inventory/models.py
from django.db import models
import uuid

# Section model
class Section(models.Model):
    SECTION_TYPE_CHOICES = [
        ('depozit', 'Depozit'),
        ('livrare', 'Zona de Livrare'),
        ('receptie', 'Zona de Recepție'),
        ('procesare', 'Procesare'),
        ('unknown', 'Unknown'),
    ]

    code = models.CharField(max_length=50, unique=True, blank=True)
    nume_custom = models.CharField(max_length=50, unique=True)  # Nume personalizat pentru secțiune
    tip_sectie = models.CharField(max_length=20, choices=SECTION_TYPE_CHOICES, default="unknown")  # Tipul secțiunii
    max_capacity = models.IntegerField()  # Capacitate maximă de cutii
    current_capacity = models.IntegerField(default=0)  # Numărul curent de cutii

    def __str__(self):
        return f"{self.nume_custom} ({self.get_tip_sectie_display()})"

    def save(self, *args, **kwargs):
        if not self.code:
            # Generează un cod unic simplu folosind o parte din uuid
            self.code = str(uuid.uuid4()).split('-')[0].upper()
        super().save(*args, **kwargs)

    def is_full(self):
        """Verifică dacă secțiunea este plină"""
        return self.current_capacity >= self.max_capacity

    def add_box(self, box):
        """Adaugă o cutie în secțiune dacă nu este plină"""
        if not self.is_full():
            box.section = self
            box.save()
            self.current_capacity += 1
            self.save()
        else:
            raise Exception("Secțiunea este plină. Nu se mai pot adăuga cutii.")

    def remove_box(self, box):
        """Mută o cutie în secțiunea 'unknown'"""
        unknown_section = Section.objects.get(tip_sectie='unknown')
        box.section = unknown_section
        box.save()
        self.current_capacity -= 1
        self.save()

    def delete_box(self, box):
        """Șterge o cutie din secțiunea 'unknown' sau 'procesare'"""
        if self.tip_sectie in ['unknown', 'procesare']:
            box.delete()
            self.current_capacity -= 1
            self.save()
        else:
            raise Exception("Cutia poate fi ștearsă doar din secțiunea 'unknown' sau 'procesare'.")

    def process_box(self, box):
        """Mută cutia în secțiunea 'procesare' și apoi o șterge"""
        procesare_section = Section.objects.get(tip_sectie='procesare')
        box.section = procesare_section
        box.save()
        procesare_section.current_capacity += 1
        procesare_section.save()

        # După mutare, se șterge cutia
        procesare_section.delete_box(box)

    def move_box(self, box, target_section):
        """Mută o cutie din secțiunea curentă în alta"""
        if self.tip_sectie in ['unknown', 'procesare']:
            raise Exception("Nu se pot muta cutii din secțiunea 'unknown' sau 'procesare' direct.")
        elif target_section.is_full():
            raise Exception(f"Secțiunea țintă {target_section.nume_custom} este plină.")
        else:
            self.current_capacity -= 1
            self.save()
            target_section.add_box(box)


# Box model
class Box(models.Model):
    COLOR_CHOICES = [
        ('albastru', 'Albastru'),
        ('rosu', 'Rosu'),
        ('verde', 'Verde'),
        ('simple', 'Bej'),  # 'simple' înseamnă Bej
    ]
    STATUS_CHOICES = [
        ('sold', 'Sold'),
        ('in_stoc', 'In Stoc'),
    ]

    code = models.CharField(max_length=3, unique=True, blank=True)  # Cod unic de 3 caractere
    name = models.CharField(max_length=100)  # Numele cutiei
    color = models.CharField(max_length=10, choices=COLOR_CHOICES)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='in_stoc')
    price = models.IntegerField()  # Prețul cutiei
    section = models.ForeignKey(Section, on_delete=models.CASCADE, null=True, blank=True)  # Secțiunea în care se află cutia
    image = models.ImageField(upload_to='box_images/', blank=True, null=True, default='box_images/default.jpg')  # Imaginea cutiei

    class Meta:
        ordering = ['color', 'code', 'price']

    def __str__(self):
        return f"{self.get_color_display()} Box - {self.name} ({self.code})"

    def save(self, *args, **kwargs):
        if not self.code:
            # Generează un cod unic de 3 caractere. Atenție: pentru producție se poate dori o metodă mai robustă.
            self.code = str(uuid.uuid4()).split('-')[0][:6].upper()
        super().save(*args, **kwargs)

    def remove_from_section(self):
        """Mută cutia în secțiunea 'unknown'"""
        unknown_section = Section.objects.get(tip_sectie='unknown')
        self.section = unknown_section
        self.save()

    def delete_box(self):
        """Șterge cutia, dar numai dacă se află în secțiunea 'unknown' sau 'procesare'"""
        if self.section and self.section.tip_sectie in ['unknown', 'procesare']:
            self.delete()
        else:
            raise Exception("Cutia trebuie să fie în 'unknown' sau 'procesare' pentru a fi ștearsă.")

    def move_to(self, target_section):
        """Mută cutia în secțiunea specificată"""
        current_section = self.section
        if current_section:
            current_section.move_box(self, target_section)
        else:
            # Dacă nu este atribuită nicio secțiune, atribuim direct secțiunea țintă
            target_section.add_box(self)
