from django import forms
from .models import Preset

class PresetForm(forms.ModelForm):
    # This __init__ method is the crucial part. It intercepts the
    # 'is_official' argument before the form is built.
    def __init__(self, *args, **kwargs):
        is_official = kwargs.pop('is_official', False)
        super().__init__(*args, **kwargs)
        
        # If the user is NOT official, remove the field from the form
        if not is_official:
            if 'official' in self.fields:
                self.fields.pop('official')

    class Meta:
        model = Preset
        fields = [
            'preset_name', 
            'flags', 
            'description', 
            'arguments', 
            'official', 
            'hidden'
        ]

        labels = {
            'hidden': 'Hide Flags (for mystery seeds)',
        }