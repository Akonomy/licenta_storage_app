

# apps/robot_interface/models.py

from django.db import models
from django.contrib.auth import get_user_model
from apps.inventory.models import Box, Section

User = get_user_model()


class Task(models.Model):
    TASK_STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('accepted', 'Accepted'),
        ('rejected', 'Rejected'),
        ('in_progress', 'In Progress'),
        ('completed', 'Completed'),
        ('failed', 'Failed'),
    ]

    TASK_TYPE_CHOICES = [
        ('move_box', 'Move Box'),
        ('add_box', 'Add Box'),
        ('remove_box', 'Remove Box'),
        ('custom_action', 'Custom Action'),
        ('emergency', 'Emergency'),
        ('park', 'Park'),
    ]

    task_type = models.CharField(max_length=20, choices=TASK_TYPE_CHOICES)
    status = models.CharField(max_length=20, choices=TASK_STATUS_CHOICES, default='pending')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    box = models.ForeignKey(Box, null=True, blank=True, on_delete=models.SET_NULL)
    source_section = models.ForeignKey(Section, null=True, blank=True, related_name='source_tasks', on_delete=models.SET_NULL)
    target_section = models.ForeignKey(Section, null=True, blank=True, related_name='target_tasks', on_delete=models.SET_NULL)
    custom_action = models.CharField(max_length=255, blank=True, null=True)
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)

    reason = models.TextField(blank=True, null=True)  # For rejection reasons or error messages

    def __str__(self):
        return f"{self.task_type} - {self.status}"

    
    @staticmethod
    def is_box_in_task(box):
        """Check if a given box is associated with any pending task."""
        return Task.objects.filter(box=box, status='pending').exists()





class RobotStatus(models.Model):
    STATUS_CHOICES = [
        ('idle', 'Idle'),
        ('busy', 'Busy'),
        ('error', 'Error'),
        ('emergency', 'Emergency'),
    ]

    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='idle')
    message = models.TextField(blank=True, null=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Robot is {self.status}"