import requests 
import json   
import pygsheets
from datetime import datetime  
from django.conf import settings 
from django.shortcuts import render, get_object_or_404, redirect
from django.core.exceptions import PermissionDenied
from django.contrib.auth.decorators import login_required
from django.db.models import Q
from django.http import JsonResponse
from allauth.socialaccount.models import SocialAccount
from . import flag_processor

from .models import Preset, UserPermission
from .forms import PresetForm
from .decorators import discord_login_required

# --- Helper Function ---

def get_silly_things_list():
    """
    Reads the silly things text file and returns a list of lines.
    Returns an empty list if the file is not found.
    """
    try:
        file_path = settings.BASE_DIR.parent / 'seedbot2000' / 'db' / 'silly_things_for_seedbot_to_say.txt'
        with open(file_path, 'r', encoding='utf-8') as f:
            lines = [line.strip() for line in f if line.strip()]
        return lines
    except FileNotFoundError:
        print("silly_things_for_seedbot_to_say.txt not found.")
        return ["Let's find some treasure!"]

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
    
def write_to_gsheets(metrics_data):
    """
    Writes a row of data to the SeedBot Metrics Google Sheet.
    """
    try:
        keyfile_path = settings.BASE_DIR.parent / 'seedbot2000' / 'db' / 'seedbot-metrics-56ffc0ce1d4f.json'
        
        gc = pygsheets.authorize(service_file=str(keyfile_path))
        sh = gc.open('SeedBot Metrics')
        wks = sh[0] 

        values_to_insert = [
            metrics_data.get('creator_id'),
            metrics_data.get('creator_name'),
            metrics_data.get('seed_type'),
            metrics_data.get('random_sprites', 'N/A'),
            metrics_data.get('share_url'),
            metrics_data.get('timestamp'),
            metrics_data.get('server_name', 'WebApp'),
            metrics_data.get('server_id', 'N/A'),
            metrics_data.get('channel_name', 'N/A'),
            metrics_data.get('channel_id', 'N/A'),
        ]
        
        wks.append_table(values=values_to_insert, start='A1', end=None, dimension='ROWS', overwrite=False)
        print("Successfully wrote to Google Sheet.")

    except Exception as e:
        print(f'Unable to write to gsheets because of:\n{e}')

# --- Views ---

def preset_list_view(request):
    queryset = Preset.objects.exclude(preset_name='').order_by('-gen_count', 'preset_name')
    query = request.GET.get('q')
    if query:
        queryset = queryset.filter(
            Q(preset_name__icontains=query) |
            Q(description__icontains=query) |
            Q(creator_name__icontains=query)
        )
    silly_things = get_silly_things_list()
    silly_things_json = json.dumps(silly_things)
    
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
        'user_discord_id': user_discord_id,
        'silly_things_json': silly_things_json,
    }
    return render(request, 'presets/preset_list.html', context)

def preset_detail_view(request, pk):
    preset = get_object_or_404(Preset, pk=pk)
    is_owner = False
    silly_things = get_silly_things_list()
    silly_things_json = json.dumps(silly_things)
    
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
        'is_owner': is_owner,
        'silly_things_json': silly_things_json,

    }
    return render(request, 'presets/preset_detail.html', context)

def roll_seed_view(request, pk):
    preset = get_object_or_404(Preset, pk=pk)
    seed_url = None
    api_error = None

    if request.method == 'POST':
        api_url = "https://api.ff6worldscollide.com/api/seed"
        
        original_flags = preset.flags
        arguments = preset.arguments
        final_flags = flag_processor.apply_args(original_flags, arguments)

        payload = {
            "key": settings.WC_API_KEY, 
            "flags": final_flags
        }
        headers = {"Content-Type": "application/json"}

        try:
            response = requests.post(api_url, data=json.dumps(payload), headers=headers, timeout=30)
            response.raise_for_status() 
            
            data = response.json()
            seed_url = data.get('url')

            preset.gen_count += 1
            preset.save()

            if seed_url:
                    creator_id, creator_name = (None, None)
                    if request.user.is_authenticated:
                        try:
                            # Get Discord info if the user is logged in
                            discord_account = request.user.socialaccount_set.get(provider='discord')
                            creator_id = discord_account.uid
                            creator_name = discord_account.extra_data.get('username', request.user.username)
                        except SocialAccount.DoesNotExist:
                            pass # User is logged in but not with Discord

                    metrics_data = {
                        'creator_id': creator_id,
                        'creator_name': creator_name,
                        'seed_type': preset.preset_name,
                        'share_url': seed_url,
                        'timestamp': datetime.utcnow().isoformat(),
                    }
                    write_to_gsheets(metrics_data)

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

@discord_login_required
def my_presets_view(request):
    user_presets = []
    silly_things = get_silly_things_list()
    silly_things_json = json.dumps(silly_things)
    try:
        discord_account = request.user.socialaccount_set.get(provider='discord')
        discord_id = discord_account.uid
        user_presets = Preset.objects.filter(creator_id=discord_id).order_by('preset_name')
    except SocialAccount.DoesNotExist:
        pass

    context = {
        'presets': user_presets,
        'silly_things_json': silly_things_json,
    }
    return render(request, 'presets/my_presets.html', context)

@discord_login_required 
def preset_create_view(request):
    discord_account = request.user.socialaccount_set.get(provider='discord')
    is_official = user_is_official(discord_account.uid)

    if request.method == 'POST':
        form = PresetForm(request.POST, is_official=is_official)
        if form.is_valid():
            preset = form.save(commit=False)
            preset.creator_id = discord_account.uid
            preset.creator_name = discord_account.extra_data.get('username', request.user.username)
            preset.save()
            return redirect('my-presets')
    else:
        form = PresetForm(is_official=is_official)

    context = {'form': form, 'preset': None}
    return render(request, 'presets/preset_form.html', context)

@discord_login_required
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
            # The form.save() method returns the saved object
            saved_preset = form.save()
            # Redirect to the detail page for the preset we just saved
            return redirect('preset-detail', pk=saved_preset.pk)
    else:
        form = PresetForm(instance=preset, is_official=is_official)

    context = {
        'form': form,
        'preset': preset
    }
    return render(request, 'presets/preset_form.html', context)

@discord_login_required
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

def connect_discord_view(request):
    return render(request, 'presets/connect_discord.html')

def roll_seed_api_view(request, pk):
    if request.method != 'POST':
        return JsonResponse({'error': 'Invalid request method'}, status=405)

    preset = get_object_or_404(Preset, pk=pk)

    # (This logic is the same as your old roll_seed_view)
    original_flags = preset.flags
    arguments = preset.arguments
    final_flags = flag_processor.apply_args(original_flags, arguments)

    api_url = "https://api.ff6worldscollide.com/api/seed"
    payload = {"key": settings.WC_API_KEY, "flags": final_flags}
    headers = {"Content-Type": "application/json"}

    try:
        response = requests.post(api_url, data=json.dumps(payload), headers=headers, timeout=30)
        response.raise_for_status()
        data = response.json()
        seed_url = data.get('url')

        preset.gen_count += 1
        preset.save()

        # On success, return a JSON object with the URL
        return JsonResponse({'seed_url': seed_url})

    except requests.exceptions.RequestException as e:
        status_code = e.response.status_code if e.response else "N/A"
        error_message = f"API Error (Status: {status_code})"
        # On failure, return a JSON object with the error
        return JsonResponse({'error': error_message}, status=400)