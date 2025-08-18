import requests 
import json     
import pygsheets
from datetime import datetime
from django.conf import settings 
from django.shortcuts import render, get_object_or_404, redirect
from django.core.exceptions import PermissionDenied
from django.db.models import Q, Count
from django.http import JsonResponse
from allauth.socialaccount.models import SocialAccount
from celery.result import AsyncResult
import os

from . import flag_processor
from .models import Preset, UserPermission, FeaturedPreset, SeedLog
from .forms import PresetForm
from .decorators import discord_login_required
from .tasks import create_local_seed_task

# --- Constants ---
SORT_OPTIONS = {
    'name': 'preset_name', '-name': '-preset_name',
    'creator': 'creator_name', '-creator': '-creator_name',
    'count': 'gen_count', '-count': '-gen_count',
}
DEFAULT_SORT = '-gen_count'

# --- Helper Functions ---
def get_silly_things_list():
    """Reads the silly things text file and returns a list of lines."""
    try:
        file_path = settings.BASE_DIR.parent / 'seedbot2000' / 'db' / 'silly_things_for_seedbot_to_say.txt'
        with open(file_path, 'r', encoding='utf-8') as f:
            lines = [line.strip() for line in f if line.strip()]
        return lines
    except FileNotFoundError:
        print("silly_things_for_seedbot_to_say.txt not found.")
        return ["Let's find some treasure!"]

def user_is_official(user_id):
    """Helper function to check if a user can create 'Official' presets."""
    try:
        permissions = UserPermission.objects.get(user_id=user_id)
        return permissions.bot_admin == 1 or permissions.race_admin == 1
    except UserPermission.DoesNotExist:
        return False

def user_is_race_admin(user_id):
    """Helper function to check if a user can feature presets."""
    try:
        permissions = UserPermission.objects.get(user_id=user_id)
        return permissions.race_admin == 1
    except UserPermission.DoesNotExist:
        return False
    
def write_to_gsheets(metrics_data):
    """Writes a row of data to the SeedBot Metrics Google Sheet."""
    try:
        keyfile_path = settings.BASE_DIR.parent / 'seedbot2000' / 'db' / 'seedbot-metrics-56ffc0ce1d4f.json'
        gc = pygsheets.authorize(service_file=str(keyfile_path))
        sh = gc.open('SeedBot Metrics')
        wks = sh[0]
        values_to_insert = [
            metrics_data.get('creator_id'), metrics_data.get('creator_name'),
            metrics_data.get('seed_type'), metrics_data.get('random_sprites', 'N/A'),
            metrics_data.get('share_url'), metrics_data.get('timestamp'),
            metrics_data.get('server_name', 'WebApp'), metrics_data.get('server_id', 'N/A'),
            metrics_data.get('channel_name', 'N/A'), metrics_data.get('channel_id', 'N/A'),
        ]
        wks.append_table(values=values_to_insert, start='A1', end=None, dimension='ROWS', overwrite=False)
        print("Successfully wrote to Google Sheet.")
    except Exception as e:
        print(f'Unable to write to gsheets because of:\n{e}')

# --- Main Views ---

def preset_list_view(request):
    sort_key = request.GET.get('sort', DEFAULT_SORT)
    order_by_field = SORT_OPTIONS.get(sort_key, DEFAULT_SORT)
    
    featured_preset_pks = list(FeaturedPreset.objects.values_list('preset_name', flat=True))
    featured_presets = Preset.objects.filter(pk__in=featured_preset_pks).order_by(order_by_field)
    queryset = Preset.objects.exclude(pk__in=featured_preset_pks).exclude(preset_name='').order_by(order_by_field)
    
    query = request.GET.get('q')
    if query:
        queryset = queryset.filter(
            Q(preset_name__icontains=query) |
            Q(description__icontains=query) |
            Q(creator_name__icontains=query)
        )
        
    is_race_admin = False
    user_discord_id = None
    if request.user.is_authenticated:
        try:
            discord_account = request.user.socialaccount_set.get(provider='discord')
            user_discord_id = int(discord_account.uid)
            is_race_admin = user_is_race_admin(user_discord_id)
        except (SocialAccount.DoesNotExist):
            pass

    silly_things = get_silly_things_list()
    silly_things_json = json.dumps(silly_things)

    context = {
        'featured_presets': featured_presets,
        'presets': queryset,
        'search_query': query if query else '',
        'user_discord_id': user_discord_id,
        'silly_things_json': silly_things_json,
        'current_sort': sort_key,
        'is_race_admin': is_race_admin, 
    }
    return render(request, 'presets/preset_list.html', context)

def preset_detail_view(request, pk):
    preset = get_object_or_404(Preset, pk=pk)
    is_owner = False
    if request.user.is_authenticated:
        try:
            discord_id = request.user.socialaccount_set.get(provider='discord').uid
            if preset.creator_id == int(discord_id):
                is_owner = True
        except SocialAccount.DoesNotExist:
            pass

    silly_things = get_silly_things_list()
    silly_things_json = json.dumps(silly_things)
    context = {
        'preset': preset,
        'is_owner': is_owner,
        'silly_things_json': silly_things_json,
    }
    return render(request, 'presets/preset_detail.html', context)

@discord_login_required
def my_presets_view(request):
    discord_account = request.user.socialaccount_set.get(provider='discord')
    discord_id_int = int(discord_account.uid)

    # --- ADDED: Calculate is_race_admin for the logged in user ---
    is_race_admin = user_is_race_admin(discord_id_int)

    # --- STATS CALCULATION ---
    all_user_rolls = SeedLog.objects.filter(creator_id=discord_id_int)
    total_rolls = all_user_rolls.count()
    favorite_preset_query = all_user_rolls.values('seed_type').annotate(roll_count=Count('seed_type')).order_by('-roll_count').first()
    favorite_preset = favorite_preset_query if favorite_preset_query else "N/A"
    
    # ... (Sorting logic for recent_rolls is unchanged) ...
    all_rolls_list = list(all_user_rolls)
    try:
        sorted_rolls = sorted(
            all_rolls_list,
            key=lambda roll: datetime.strptime(roll.timestamp, '%b %d %Y %H:%M:%S'),
            reverse=True
        )
    except ValueError:
        sorted_rolls = all_rolls_list
    recent_rolls = sorted_rolls[:10]

    # --- My Presets List (existing logic) ---
    sort_key = request.GET.get('sort', 'name')
    order_by_field = SORT_OPTIONS.get(sort_key, 'preset_name')
    query = request.GET.get('q')
    user_presets = Preset.objects.filter(creator_id=discord_id_int)
    if query:
        user_presets = user_presets.filter(Q(preset_name__icontains=query) | Q(description__icontains=query))
    user_presets = user_presets.order_by(order_by_field)

    # --- ADDED: Get silly things for the template ---
    silly_things = get_silly_things_list()
    silly_things_json = json.dumps(silly_things)
    
    context = {
        'presets': user_presets,
        'current_sort': sort_key,
        'search_query': query if query else '',
        'user_discord_id': discord_id_int,
        'total_rolls': total_rolls,
        'favorite_preset': favorite_preset,
        'recent_rolls': recent_rolls,
        # --- ADDED: Missing context variables ---
        'is_race_admin': is_race_admin,
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
    discord_account = request.user.socialaccount_set.get(provider='discord')
    
    if preset.creator_id != int(discord_account.uid):
        raise PermissionDenied

    is_official = user_is_official(discord_account.uid)

    if request.method == 'POST':
        form = PresetForm(request.POST, instance=preset, is_official=is_official)
        if form.is_valid():
            saved_preset = form.save()
            return redirect('preset-detail', pk=saved_preset.pk)
    else:
        form = PresetForm(instance=preset, is_official=is_official)

    context = {'form': form, 'preset': preset}
    return render(request, 'presets/preset_form.html', context)

@discord_login_required
def preset_delete_view(request, pk):
    preset = get_object_or_404(Preset, pk=pk)
    discord_account = request.user.socialaccount_set.get(provider='discord')
    
    if preset.creator_id != int(discord_account.uid):
        raise PermissionDenied

    if request.method == 'POST':
        preset.delete()
        return redirect('my-presets')

    context = {'preset': preset}
    return render(request, 'presets/preset_confirm_delete.html', context)

# --- API / AJAX Views ---

@discord_login_required
def roll_seed_dispatcher_view(request, pk):
    if request.method != 'POST':
        return JsonResponse({'error': 'Invalid request method'}, status=405)

    preset = get_object_or_404(Preset, pk=pk)
    args_list = [arg.strip() for arg in preset.arguments.split()] if preset.arguments else []
    
    local_roll_args = {
        'practice', 'doors', 'dungeoncrawl', 'doorslite', 'maps', 
        'mapx', 'lg1', 'lg2', 'ws', 'csi', 'tunes', 'ctunes'
    }
    
    discord_account = request.user.socialaccount_set.get(provider='discord')
    discord_id = int(discord_account.uid)
    discord_name = discord_account.extra_data.get('username', request.user.username)

    if any(arg in local_roll_args for arg in args_list):
        task = create_local_seed_task.delay(pk, discord_id, discord_name)
        return JsonResponse({'method': 'local', 'task_id': task.id})
    else:
        final_flags = flag_processor.apply_args(preset.flags, preset.arguments)
        api_url = "https://api.ff6worldscollide.com/api/seed"
        payload = {"key": settings.WC_API_KEY, "flags": final_flags}
        headers = {"Content-Type": "application/json"}
        try:
            response = requests.post(api_url, data=json.dumps(payload), headers=headers, timeout=30)
            response.raise_for_status()
            data = response.json()
            seed_url = data.get('url')
            
            preset.gen_count += 1
            preset.save(update_fields=['gen_count'])

            timestamp = datetime.now().strftime('%b %d %Y %H:%M:%S')


            SeedLog.objects.create(
                creator_id=discord_id,
                creator_name=discord_name,
                seed_type=preset.preset_name,
                share_url=seed_url,
                timestamp=datetime.now().strftime('%b %d %Y %H:%M:%S'),
                server_name='WebApp'
            )

            metrics_data = {
                'creator_id': discord_id,
                'creator_name': discord_name,
                'seed_type': preset.preset_name,
                'share_url': seed_url,
                'timestamp': timestamp,
            }
            write_to_gsheets(metrics_data)

            return JsonResponse({'method': 'api', 'seed_url': seed_url})
        except requests.exceptions.RequestException as e:
            error_message = "The FF6WC API returned an error. Please check your flags."
            return JsonResponse({'error': error_message}, status=400)


def get_local_seed_roll_status_view(request, task_id):
    """
    Checks the status of a Celery task and returns the result,
    including custom progress states.
    """
    task_result = AsyncResult(task_id)
    response_data = {
        'task_id': task_id,
        'status': task_result.status,
        'result': None
    }

    if task_result.state == 'SUCCESS':
        response_data['result'] = task_result.result
    elif task_result.state == 'FAILURE':
        # task_result.info is the exception, which is more descriptive
        response_data['result'] = str(task_result.info)
    elif task_result.state == 'PROGRESS':
        # task_result.info is the 'meta' dictionary we passed
        response_data['result'] = task_result.info.get('status', 'Processing...')
    
    return JsonResponse(response_data)


@discord_login_required
def toggle_feature_view(request, pk):
    if request.method != 'POST':
        return JsonResponse({'error': 'Invalid request method'}, status=405)

    discord_id = request.user.socialaccount_set.get(provider='discord').uid
    if not user_is_race_admin(discord_id):
         raise PermissionDenied("You do not have permission to feature presets.")

    preset = get_object_or_404(Preset, pk=pk)
    featured_obj, created = FeaturedPreset.objects.get_or_create(preset_name=preset.pk)
    
    if created:
        return JsonResponse({'status': 'success', 'featured': True})
    else:
        featured_obj.delete()
        return JsonResponse({'status': 'success', 'featured': False})