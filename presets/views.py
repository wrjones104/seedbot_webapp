import requests 
import json     
from django.conf import settings 
from django.shortcuts import render, get_object_or_404, redirect
from django.core.exceptions import PermissionDenied
from django.contrib.auth.decorators import login_required
from django.db.models import Q
from allauth.socialaccount.models import SocialAccount

from .models import Preset, UserPermission
from .forms import PresetForm

# --- Helper Function ---

def user_is_official(user_id):
    """Helper function to check a user's admin status from the database."""
    try:
        # Query the UserPermission table for the user's ID
        permissions = UserPermission.objects.get(user_id=user_id)
        # Return True if either admin flag is set to 1
        return permissions.bot_admin == 1 or permissions.race_admin == 1
    except UserPermission.DoesNotExist:
        # If the user isn't in the table, they're not an admin
        return False

# --- Views ---

def preset_list_view(request):
    queryset = Preset.objects.exclude(preset_name='').order_by('preset_name')
    query = request.GET.get('q')
    if query:
        queryset = queryset.filter(
            Q(preset_name__icontains=query) |
            Q(description__icontains=query) |
            Q(creator_name__icontains=query)
        )
    
    # Get the logged-in user's Discord ID, if they have one
    user_discord_id = None
    if request.user.is_authenticated:
        try:
            user_discord_id = int(request.user.socialaccount_set.get(provider='discord').uid)
        except (SocialAccount.DoesNotExist, AttributeError):
            pass

    context = {
        'presets': queryset,
        'search_query': query if query else '',
        'user_discord_id': user_discord_id, # Pass ID to template
    }
    return render(request, 'presets/preset_list.html', context)

def preset_detail_view(request, pk):
    preset = get_object_or_404(Preset, pk=pk)
    is_owner = False
    
    # Check if the current user is the owner of the preset
    if request.user.is_authenticated:
        try:
            discord_id = request.user.socialaccount_set.get(provider='discord').uid
            if preset.creator_id == int(discord_id):
                is_owner = True
        except SocialAccount.DoesNotExist:
            pass # User is logged in but not with Discord

    context = {
        'preset': preset,
        'is_owner': is_owner, # Pass the ownership flag to the template
    }
    return render(request, 'presets/preset_detail.html', context)

def roll_seed_view(request, pk):
    preset = get_object_or_404(Preset, pk=pk)
    seed_url = None
    api_error = None

    if request.method == 'POST':
        api_url = "https://api.ff6worldscollide.com/api/seed"
        
        payload = {
            "key": settings.WC_API_KEY, 
            "flags": preset.flags
        }
        headers = {"Content-Type": "application/json"}

        try:
            response = requests.post(api_url, data=json.dumps(payload), headers=headers, timeout=30)
            response.raise_for_status() 
            
            data = response.json()
            seed_url = data.get('url')

            preset.gen_count += 1
            preset.save()

        except requests.exceptions.RequestException as e:
            status_code = e.response.status_code if e.response else "N/A"
            api_error = f"Failed to generate seed. The API returned an error (Status: {status_code})."
            print(f"API Error: {e}") 

    context = {
        'preset': preset,
        'seed_url': seed_url,
        'api_error': api_error,
    }
    return render(request, 'presets/preset_detail.html', context)

@login_required
def my_presets_view(request):
    user_presets = []
    try:
        discord_account = request.user.socialaccount_set.get(provider='discord')
        discord_id = discord_account.uid
        user_presets = Preset.objects.filter(creator_id=discord_id).order_by('preset_name')
    except SocialAccount.DoesNotExist:
        pass

    context = {
        'presets': user_presets
    }
    return render(request, 'presets/my_presets.html', context)

@login_required
def preset_create_view(request):
    is_official = False
    try:
        discord_id = request.user.socialaccount_set.get(provider='discord').uid
        is_official = user_is_official(discord_id)
    except SocialAccount.DoesNotExist:
        pass

    if request.method == 'POST':
        form = PresetForm(request.POST, is_official=is_official)
        if form.is_valid():
            preset = form.save(commit=False)
            
            discord_account = request.user.socialaccount_set.get(provider='discord')
            preset.creator_id = discord_account.uid
            preset.creator_name = discord_account.user.username
            preset.save()
            return redirect('my-presets')
    else:
        form = PresetForm(is_official=is_official)

    context = {
        'form': form,
        'preset': None # To make the template title conditional work
    }
    return render(request, 'presets/preset_form.html', context)

@login_required
def preset_update_view(request, pk):
    preset = get_object_or_404(Preset, pk=pk)
    
    try:
        discord_id = request.user.socialaccount_set.get(provider='discord').uid
        if preset.creator_id != int(discord_id):
            raise PermissionDenied
        is_official = user_is_official(discord_id)
    except (SocialAccount.DoesNotExist, AttributeError):
        raise PermissionDenied

    if request.method == 'POST':
        form = PresetForm(request.POST, instance=preset, is_official=is_official)
        if form.is_valid():
            form.save()
            return redirect('my-presets')
    else:
        form = PresetForm(instance=preset, is_official=is_official)

    context = {
        'form': form,
        'preset': preset
    }
    return render(request, 'presets/preset_form.html', context)

@login_required
def preset_delete_view(request, pk):
    preset = get_object_or_404(Preset, pk=pk)
    
    try:
        discord_id = request.user.socialaccount_set.get(provider='discord').uid
        if preset.creator_id != int(discord_id):
            raise PermissionDenied
    except (SocialAccount.DoesNotExist, AttributeError):
        raise PermissionDenied

    if request.method == 'POST':
        preset.delete()
        return redirect('my-presets')

    context = {
        'preset': preset
    }
    return render(request, 'presets/preset_confirm_delete.html', context)