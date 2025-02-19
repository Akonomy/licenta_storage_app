# apps/robot_interface/serializers.py

from rest_framework import serializers
from .models import Task, RobotStatus

class TaskSerializer(serializers.ModelSerializer):
    class Meta:
        model = Task
        fields = '__all__'

class RobotStatusSerializer(serializers.ModelSerializer):
    class Meta:
        model = RobotStatus
        fields = '__all__'
