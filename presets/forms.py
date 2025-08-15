import requests
import json
from django import forms
from django.conf import settings
from .models import Preset
from profanity import profanity # <-- This is the corrected import

# (ARGUMENT_CHOICES list is unchanged)
ARGUMENT_CHOICES = [
    ('paint', 'Paint'), ('kupo', 'Kupo'), ('loot', 'Loot'), ('fancygau', 'Fancy Gau'),
    ('hundo', 'Hundo'), ('objectives', 'Objectives'), ('nospoilers', 'No Spoilers'),
    ('spoilers', 'Spoilers'), ('noflashes', 'No Flashes'), ('dash', 'Dash'),
    ('emptyshops', 'Empty Shops'), ('emptychests', 'Empty Chests'), ('yeet', 'Yeet'),
    ('cg', 'CG'), ('palette', 'Palette'), ('mystery', 'Mystery'), ('doors', 'Doors'),
    ('practice', 'Practice'), ('dev', 'Dev'), ('dungeoncrawl', 'Dungeon Crawl'),
    ('doorslite', 'Doors Lite'), ('maps', 'Maps'), ('mapx', 'Map-X'), ('ap', 'AP'),
    ('apts', 'APTS'), ('flagsonly', 'Flags Only'), ('steve', 'Steve'), ('zozo', 'Zozo'),
    ('desc', 'Desc'), ('lg1', 'LG1'), ('lg2', 'LG2'), ('ws', 'WS'), ('csi', 'CSI')
]

class PresetForm(forms.ModelForm):
    arguments = forms.MultipleChoiceField(
        choices=ARGUMENT_CHOICES,
        widget=forms.SelectMultiple,
        required=False,
        label="Arguments"
    )

    def __init__(self, *args, **kwargs):
        is_official = kwargs.pop('is_official', False)
        super().__init__(*args, **kwargs)
        if self.instance and self.instance.pk and self.instance.arguments:
            self.fields['arguments'].initial = self.instance.arguments.split()
        if not is_official:
            if 'official' in self.fields:
                self.fields.pop('official')

    def save(self, commit=True):
        selected_args = self.cleaned_data.get('arguments', [])
        self.instance.arguments = ' '.join(selected_args)
        return super().save(commit=commit)

    def clean(self):
        cleaned_data = super().clean()
        name = cleaned_data.get("preset_name")
        description = cleaned_data.get("description")
        flags = cleaned_data.get("flags")

        # 1. Check preset name for profanity (fast check)
        if name and profanity.contains_profanity(name): # <-- Corrected function call
            self.add_error('preset_name', "Watch your mouth, dirtbag!.")

        # 2. Check description for profanity (fast check)
        if description and profanity.contains_profanity(description): # <-- Corrected function call
            self.add_error('description', "Watch your mouth, dirtbag!")
            
        if self.errors:
            return cleaned_data

        # 3. If everything is clean so far, check the flags via API (slow check)
        if flags:
            print(f"Validating flags: {flags}")
            api_url = "https://api.ff6worldscollide.com/api/seed"
            payload = {"key": settings.WC_API_KEY, "flags": flags}
            headers = {"Content-Type": "application/json"}

            try:
                response = requests.post(api_url, data=json.dumps(payload), headers=headers, timeout=30)
                response.raise_for_status()
            except requests.exceptions.RequestException as e:
                error_message = "These flags are invalid."
                if e.response:
                    try:
                        api_error = e.response.json().get('error', 'API returned an error.')
                        error_message = f"Invalid Flags: {api_error}"
                    except json.JSONDecodeError:
                        error_message = "Invalid Flags: The API returned an unreadable error."
                self.add_error('flags', error_message)
        
        return cleaned_data

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