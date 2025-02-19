from django.db import models
from apps.inventory.models import Box
from django.conf import settings
from django.core.exceptions import ValidationError

# Order Model with Status, Addresses, and Payment Information
class Order(models.Model):
    ORDER_STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('shipped', 'Shipped'),
        ('delivered', 'Delivered'),
        ('canceled', 'Canceled'),
    ]

    PAYMENT_STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('completed', 'Completed'),
        ('failed', 'Failed'),
    ]

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    ordered_date = models.DateTimeField(auto_now_add=True)
    status = models.CharField(max_length=10, choices=ORDER_STATUS_CHOICES, default='pending')
    payment_status = models.CharField(max_length=10, choices=PAYMENT_STATUS_CHOICES, default='pending')
    total_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)  # Dynamically updated
    shipping_address = models.CharField(max_length=255, blank=True, null=True)
    billing_address = models.CharField(max_length=255, blank=True, null=True)
    is_ordered = models.BooleanField(default=False)

    def __str__(self):
        return f"Order {self.id} by {self.user.username} (Status: {self.get_status_display()})"

    def calculate_total(self):
        """Calculate the total price for all items in the order."""
        total = sum(item.get_total_price() for item in self.orderitem_set.all())
        self.total_amount = total
        self.save()

    def update_stock(self):
        """Update stock for each box in the order."""
        for item in self.orderitem_set.all():
            box = item.box
            if box.section.is_full():
                raise ValidationError(f"The section '{box.section}' is full. Cannot place the order.")
            # Deduct stock
            box.section.current_capacity -= item.quantity
            box.section.save()


# OrderItem Model with Quantity and Total Price Calculation
class OrderItem(models.Model):
    order = models.ForeignKey(Order, on_delete=models.CASCADE)
    box = models.ForeignKey(Box, on_delete=models.CASCADE)
    quantity = models.PositiveIntegerField(default=1)
    price_at_purchase = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)  # Save price at order time

    def __str__(self):
        return f"{self.quantity} x {self.box.code} in Order {self.order.id}"

    def get_total_price(self):
        """Return the total price for this item (quantity * price_at_purchase)."""
        return self.quantity * self.price_at_purchase

    def save(self, *args, **kwargs):
        """Override the save method to capture the current price of the box."""
        if not self.price_at_purchase:
            self.price_at_purchase = self.box.price  # Save price at the time of order
        super().save(*args, **kwargs)

# Order Shipping and Billing Address Models (if needed for extended functionality)
class Address(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    address_line_1 = models.CharField(max_length=255)
    address_line_2 = models.CharField(max_length=255, blank=True, null=True)
    city = models.CharField(max_length=100)
    postal_code = models.CharField(max_length=10)
    country = models.CharField(max_length=100)
    is_billing = models.BooleanField(default=False)  # True if it's a billing address

    def __str__(self):
        return f"{self.user.username}'s Address (Billing: {self.is_billing})"
