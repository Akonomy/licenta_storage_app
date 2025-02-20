# store_new/models.py
from django.db import models
from django.conf import settings
from apps.inventory.models import Box  # Pentru a lega comanda de o cutie
from django.core.validators import URLValidator
from django.core.exceptions import ValidationError

# Modelul pentru produse adăugate manual (fallback sau custom)
class Product(models.Model):
    title = models.CharField(max_length=255)
    price = models.IntegerField()  # Prețul în lei
    description = models.TextField(blank=True, null=True)
    main_image = models.URLField(max_length=500)
    # Stocăm URL-uri suplimentare ca listă (ex. în format JSON)
    secondary_images = models.JSONField(blank=True, null=True, help_text="Listă de URL-uri ale imaginilor")

    def clean(self):
        # Validator pentru URL-ul imaginii principale (exemplu de blocare domenii nedorite)
        prohibited_domains = ['adultsite.com', 'gambling.com', 'altrexplicit.com']  # Domenii exemplu
        url_validator = URLValidator()
        try:
            url_validator(self.main_image)
        except ValidationError:
            raise ValidationError("URL-ul imaginii principale nu este valid.")
        
        for domain in prohibited_domains:
            if domain in self.main_image:
                raise ValidationError("URL-ul imaginii principale provine dintr-un domeniu interzis.")

        if self.secondary_images:
            for url in self.secondary_images:
                try:
                    url_validator(url)
                except ValidationError:
                    raise ValidationError("Una dintre imaginile secundare nu este validă.")
                for domain in prohibited_domains:
                    if domain in url:
                        raise ValidationError("O imagine secundară provine dintr-un domeniu interzis.")

    def __str__(self):
        return self.title

# Modelul Comenzii
class Order(models.Model):
    ORDER_STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('processing', 'Processing'),
        ('waiting', 'Waiting'),
        ('completed', 'Completed'),
        ('canceled', 'Canceled'),
    ]
    # Toate județele din România (default: Suceava)
    COUNTY_CHOICES = [
        ('Alba', 'Alba'),
        ('Arad', 'Arad'),
        ('Argeș', 'Argeș'),
        ('Bacău', 'Bacău'),
        ('Bihor', 'Bihor'),
        ('Bistrița-Năsăud', 'Bistrița-Năsăud'),
        ('Botoșani', 'Botoșani'),
        ('Brașov', 'Brașov'),
        ('Brăila', 'Brăila'),
        ('București', 'București'),
        ('Buzău', 'Buzău'),
        ('Caraș-Severin', 'Caraș-Severin'),
        ('Călărași', 'Călărași'),
        ('Cluj', 'Cluj'),
        ('Constanța', 'Constanța'),
        ('Covasna', 'Covasna'),
        ('Dâmbovița', 'Dâmbovița'),
        ('Dolj', 'Dolj'),
        ('Galați', 'Galați'),
        ('Giurgiu', 'Giurgiu'),
        ('Gorj', 'Gorj'),
        ('Harghita', 'Harghita'),
        ('Hunedoara', 'Hunedoara'),
        ('Ialomița', 'Ialomița'),
        ('Iași', 'Iași'),
        ('Ilfov', 'Ilfov'),
        ('Maramureș', 'Maramureș'),
        ('Mehedinți', 'Mehedinți'),
        ('Mureș', 'Mureș'),
        ('Neamț', 'Neamț'),
        ('Olt', 'Olt'),
        ('Prahova', 'Prahova'),
        ('Satu Mare', 'Satu Mare'),
        ('Sălaj', 'Sălaj'),
        ('Sibiu', 'Sibiu'),
        ('Suceava', 'Suceava'),
        ('Teleorman', 'Teleorman'),
        ('Timiș', 'Timiș'),
        ('Tulcea', 'Tulcea'),
        ('Vaslui', 'Vaslui'),
        ('Vâlcea', 'Vâlcea'),
        ('Vrancea', 'Vrancea'),
    ]
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='store_new_orders')
    ordered_date = models.DateTimeField(auto_now_add=True)
    status = models.CharField(max_length=20, choices=ORDER_STATUS_CHOICES, default='pending')
    total_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    # Informații de livrare/adresă:
    county = models.CharField(max_length=100, choices=COUNTY_CHOICES, default='Suceava')
    street = models.CharField(max_length=255)
    commune = models.CharField(max_length=255, blank=True, null=True)
    # Asocierea comenzii cu o cutie (din depozit)
    package_box = models.ForeignKey(Box, on_delete=models.SET_NULL, null=True, blank=True, help_text="Cutia asociată comenzii")
    # Flag pentru comandă în așteptare (dacă nu a fost găsită o cutie liberă)
    waiting = models.BooleanField(default=False)

    def __str__(self):
        return f"Order {self.id} by {self.user.username} ({self.get_status_display()})"

    def calculate_total(self):
        total = sum(item.get_total_price() for item in self.orderitem_set.all())
        self.total_amount = total
        self.save()
        return total

    def get_delivery_region_code(self):
        """
        Returnează un cod numeric în funcție de județul de livrare.
        Codificare exemplu:
          1 - Moldova
          2 - Transilvania
          3 - Muntenia
          4 - Oltenia
          5 - Dobrogea
          6 - Banat
          7 - Alte regiuni
        """
        region_mapping = {
            1: ["Suceava", "Iași", "Botoșani", "Neamț", "Vaslui", "Bacău"],
            2: ["Cluj", "Alba", "Sibiu", "Mureș", "Bistrița-Năsăud"],
            3: ["București", "Ilfov", "Giurgiu", "Călărași", "Prahova", "Dâmbovița", "Argeș"],
            4: ["Dolj", "Gorj", "Mehedinți", "Vâlcea", "Olt"],
            5: ["Constanța", "Tulcea", "Brăila", "Buzău"],
            6: ["Timiș", "Arad", "Caraș-Severin"],
            7: ["Covasna", "Harghita", "Ialomița", "Maramureș", "Satu Mare", "Sălaj", "Hunedoara"],
        }
        for code, counties in region_mapping.items():
            if self.county in counties:
                return code
        return 0  # Cod necunoscut

# Modelul pentru elementele unei comenzi
class OrderItem(models.Model):
    order = models.ForeignKey(Order, on_delete=models.CASCADE)
    product_title = models.CharField(max_length=255)
    product_price = models.IntegerField()
    quantity = models.PositiveIntegerField(default=1)
    # Dacă produsul vine din API, se poate stoca și un id extern
    external_id = models.IntegerField(null=True, blank=True)

    def __str__(self):
        return f"{self.quantity} x {self.product_title} in Order {self.order.id}"

    def get_total_price(self):
        return self.quantity * self.product_price




class BoxQueue(models.Model):
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='box_queue')
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Coada de așteptare pentru cutii - Comanda {self.order.id} plasată la {self.created_at}"

        

class DeliveryQueue(models.Model):
    order = models.ForeignKey(Order, on_delete=models.CASCADE)
    box = models.ForeignKey(Box, on_delete=models.CASCADE)
    region_code = models.IntegerField()
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"DeliveryQueue - Order {self.order.id} (Box {self.box.id}) pentru regiunea {self.region_code}"

