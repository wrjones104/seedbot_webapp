import subprocess
import uuid
import os
import zipfile
from pathlib import Path
from datetime import datetime
from celery import shared_task
from celery.exceptions import Ignore
from django.conf import settings
from .models import Preset, SeedLog
from . import flag_processor
from .utils import write_to_gsheets

class RollException(Exception):
    """Custom exception for seed rolling errors."""
    def __init__(self, msg, filename, sperror):
        self.msg = msg
        self.sperror = sperror
        self.filename = filename
        super().__init__(self.msg)

@shared_task(bind=True)
def create_local_seed_task(self, preset_pk, user_id, user_name):
    try:
        preset = Preset.objects.get(pk=preset_pk)
    except Preset.DoesNotExist:
        raise ValueError(f"Preset with pk {preset_pk} not found.")

    final_flags = flag_processor.apply_args(preset.flags, preset.arguments)
    unique_id = str(uuid.uuid4())[:8]
    filename_base = f"{preset.preset_name.replace(' ', '_').replace('/', '-')}_{unique_id}"
    project_root = settings.BASE_DIR.parent
    seedbot2000_dir = project_root / 'seedbot2000'
    main_wc_dir = seedbot2000_dir / 'WorldsCollide'
    output_dir = main_wc_dir / 'seeds'
    output_smc = output_dir / f"{filename_base}.smc"
    output_dir.mkdir(parents=True, exist_ok=True)
    args_list = preset.arguments.split() if preset.arguments else []
    dir_map = {
        'practice': 'WorldsCollide_practice', 'doors': 'WorldsCollide_Door_Rando',
        'dungeoncrawl': 'WorldsCollide_Door_Rando', 'doorslite': 'WorldsCollide_Door_Rando',
        'maps': 'WorldsCollide_Door_Rando', 'mapx': 'WorldsCollide_Door_Rando',
        'lg1': 'WorldsCollide_location_gating1', 'lg2': 'WorldsCollide_location_gating1',
        'ws': 'WorldsCollide_shuffle_by_world', 'csi': 'WorldsCollide_shuffle_by_world',
    }
    script_dir_name = 'WorldsCollide'
    for arg in args_list:
        if arg in dir_map:
            script_dir_name = dir_map[arg]
            break
    script_dir = seedbot2000_dir / script_dir_name
    wc_script = script_dir / 'wc.py'
    command = ["python3", str(wc_script), "-i", str(main_wc_dir / 'ff3.smc'), "-o", str(output_smc)]
    command.extend(final_flags.split())
    
    try:
        subprocess.run(
            command, cwd=script_dir, capture_output=True, text=True,
            timeout=120, check=True
        )
        
        zip_filename = f"{filename_base}.zip"
        txt_path = output_smc.with_suffix('.txt')
        zip_path = output_smc.with_suffix('.zip')
        with zipfile.ZipFile(zip_path, 'w') as zf:
            zf.write(output_smc, arcname=output_smc.name)
            if txt_path.exists():
                zf.write(txt_path, arcname=txt_path.name)
        output_smc.unlink()
        if txt_path.exists(): txt_path.unlink()

        preset.gen_count += 1
        preset.save(update_fields=['gen_count'])
        
        share_url = f'{settings.MEDIA_URL}{zip_filename}'
        timestamp = datetime.now().strftime('%b %d %Y %H:%M:%S')


        SeedLog.objects.create(
            creator_id=user_id,
            creator_name=user_name,
            seed_type=preset.preset_name,
            share_url=share_url,
            timestamp=datetime.now().strftime('%b %d %Y %H:%M:%S'),
            server_name='WebApp'
        )

        metrics_data = {
            'creator_id': user_id,
            'creator_name': user_name,
            'seed_type': preset.preset_name,
            'share_url': share_url,
            'timestamp': timestamp,
        }
        write_to_gsheets(metrics_data)

        return share_url

    except Exception as e:
        err_msg = f"An error occurred: {str(e)}"
        if isinstance(e, subprocess.CalledProcessError):
            err_msg = f"The seed roller script failed: {e.stderr or e.stdout}"
        self.update_state(state='FAILURE', meta={'exc_type': type(e).__name__, 'exc_message': err_msg})
        raise Ignore()