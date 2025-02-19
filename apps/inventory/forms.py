from django import forms
from .models import Box, Section

class BoxForm(forms.ModelForm):
    add_move_task = forms.BooleanField(
        required=False,
        label='Add task to move to depozit?'
    )

    class Meta:
        model = Box
        # Eliminăm câmpul "code" deoarece acesta se generează automat
        fields = ['name', 'color', 'price', 'section', 'image', 'add_move_task']


class SectionForm(forms.ModelForm):
    class Meta:
        model = Section
        # Folosim noile nume de câmpuri: 'nume_custom' în loc de 'name' și 'tip_sectie' în loc de 'type'
        fields = ['nume_custom', 'tip_sectie', 'max_capacity']
