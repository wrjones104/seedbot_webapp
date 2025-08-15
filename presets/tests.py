from django.test import TestCase
from django import forms
from .profanity_list import PROFANITY_WORDS

# Create a simple form for testing that mirrors the PresetForm fields
# without the database dependency.
class ProfanityTestForm(forms.Form):
    preset_name = forms.CharField()
    description = forms.CharField(required=False)

    def clean_preset_name(self):
        preset_name = self.cleaned_data['preset_name']
        for word in PROFANITY_WORDS:
            if word in preset_name.lower():
                raise forms.ValidationError("Please avoid using inappropriate language in the preset name.")
        return preset_name

    def clean_description(self):
        description = self.cleaned_data['description']
        if description:
            for word in PROFANITY_WORDS:
                if word in description.lower():
                    raise forms.ValidationError("Please avoid using inappropriate language in the description.")
        return description

class PresetFormProfanityTest(TestCase):

    def test_profanity_in_preset_name(self):
        # Test that a preset name with profanity is invalid
        form_data = {
            'preset_name': 'a darn preset',
            'description': 'A test preset.',
        }
        form = ProfanityTestForm(data=form_data)
        self.assertFalse(form.is_valid())
        self.assertIn('preset_name', form.errors)
        self.assertEqual(form.errors['preset_name'][0], "Please avoid using inappropriate language in the preset name.")

    def test_profanity_in_description(self):
        # Test that a description with profanity is invalid
        form_data = {
            'preset_name': 'A test preset',
            'description': 'This is a heck of a description.',
        }
        form = ProfanityTestForm(data=form_data)
        self.assertFalse(form.is_valid())
        self.assertIn('description', form.errors)
        self.assertEqual(form.errors['description'][0], "Please avoid using inappropriate language in the description.")

    def test_no_profanity(self):
        # Test that a preset with no profanity is valid
        form_data = {
            'preset_name': 'A clean preset',
            'description': 'This is a clean description.',
        }
        form = ProfanityTestForm(data=form_data)
        self.assertTrue(form.is_valid())

    def test_profanity_in_both_fields(self):
        # Test that a preset with profanity in both fields is invalid
        form_data = {
            'preset_name': 'a gosh darn preset',
            'description': 'This is a heck of a description.',
        }
        form = ProfanityTestForm(data=form_data)
        self.assertFalse(form.is_valid())
        self.assertIn('preset_name', form.errors)
        self.assertIn('description', form.errors)
        self.assertEqual(form.errors['preset_name'][0], "Please avoid using inappropriate language in the preset name.")
        self.assertEqual(form.errors['description'][0], "Please avoid using inappropriate language in the description.")
