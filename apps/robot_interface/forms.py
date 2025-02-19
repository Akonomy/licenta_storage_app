# apps/robot_interface/forms.py

from django import forms
from .models import Task
from apps.inventory.models import Box, Section

# apps/robot_interface/forms.py

class TaskForm(forms.ModelForm):
    class Meta:
        model = Task
        fields = ['task_type', 'box', 'source_section', 'target_section', 'custom_action']
        widgets = {
            'task_type': forms.Select(attrs={'onchange': 'toggleFields()'}),
        }

    def __init__(self, *args, **kwargs):
        super(TaskForm, self).__init__(*args, **kwargs)
        # Initially hide source_section field
        self.fields['source_section'].widget = forms.HiddenInput()

    def clean(self):
        cleaned_data = super().clean()
        task_type = cleaned_data.get('task_type')
        box = cleaned_data.get('box')
        target_section = cleaned_data.get('target_section')
        custom_action = cleaned_data.get('custom_action')

        if task_type == 'move_box':
            if not box or not target_section:
                raise forms.ValidationError("Box and target section are required for moving a box.")
            # Automatically set the source_section based on the box's current location
            cleaned_data['source_section'] = box.section
        elif task_type == 'add_box':
            if not box or not target_section:
                raise forms.ValidationError("Box and target section are required for adding a box.")
        elif task_type == 'remove_box':
            if not box:
                raise forms.ValidationError("Box is required for removing a box.")
            # Automatically set the source_section based on the box's current location
            cleaned_data['source_section'] = box.section
        elif task_type == 'custom_action':
            if not custom_action:
                raise forms.ValidationError("Custom action is required for a custom task.")
        return cleaned_data
