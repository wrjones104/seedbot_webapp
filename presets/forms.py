import requests
import json
from django import forms
from django.conf import settings
from .models import Preset

# Define the list of available arguments as a constant
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
        # Change the widget from CheckboxSelectMultiple to SelectMultiple
        widget=forms.SelectMultiple,
        required=False,
        label="Arguments" # Add a clean label
    )

    def __init__(self, *args, **kwargs):
        is_official = kwargs.pop('is_official', False)
        super().__init__(*args, **kwargs)

        # This part handles pre-checking the boxes when editing a preset
        if self.instance and self.instance.pk and self.instance.arguments:
            # Get the saved string, e.g., "dash loot", and split it into a list
            self.fields['arguments'].initial = self.instance.arguments.split()

        if not is_official:
            if 'official' in self.fields:
                self.fields.pop('official')

    def save(self, commit=True):
        # This part handles converting the list of choices back into a string
        # Get the list of selected arguments, e.g., ['dash', 'loot']
        selected_args = self.cleaned_data.get('arguments', [])
        # Join them into a single space-separated string
        self.instance.arguments = ' '.join(selected_args)
        
        # Call the parent save method to save the instance
        return super().save(commit=commit)
    def clean_flags(self):
            # Get the flag string submitted by the user
            flags_data = self.cleaned_data['flags']
            
            # Don't bother validating if the flags are empty
            if not flags_data:
                return flags_data

            print(f"Validating flags: {flags_data}")
            api_url = "https://api.ff6worldscollide.com/api/seed"
            payload = {
                "key": settings.WC_API_KEY, 
                "flags": flags_data
            }
            headers = {"Content-Type": "application/json"}

            try:
                # Make a test API call to see if it succeeds
                response = requests.post(api_url, data=json.dumps(payload), headers=headers, timeout=30)
                
                # If the response is an error (like 400), it will raise an exception
                response.raise_for_status()

            except requests.exceptions.RequestException as e:
                # The API call failed, so the flags are invalid.
                # We will raise a validation error that Django will show to the user.
                error_message = "These flags are invalid."
                if e.response:
                    try:
                        # Try to get a more specific error from the API response
                        api_error = e.response.json().get('error', 'API returned an error.')
                        error_message = f"Invalid Flags: {api_error}"
                    except json.JSONDecodeError:
                        error_message = "Invalid Flags: The API returned an unreadable error."

                raise forms.ValidationError(error_message)

            # If we get here, the API call was successful, so the flags are valid.
            return flags_data

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