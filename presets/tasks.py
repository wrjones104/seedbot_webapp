import subprocess
import uuid
import os
import zipfile
from pathlib import Path
from datetime import datetime
import sys
import asyncio
import tempfile
import shutil
import traceback

from celery import shared_task
from celery.exceptions import Ignore
from django.conf import settings
from .models import Preset, SeedLog
from . import flag_processor
from .utils import write_to_gsheets

# The sys.path hack is no longer needed and can be removed.

# This is now the simple, correct way to import, thanks to your fix.
from johnnydmad import johnnydmad_webapp


class RollException(Exception):
    """Custom exception for seed rolling errors."""
    def __init__(self, msg, filename, sperror):
        self.msg = msg
        self.sperror = sperror
        self.filename = filename
        super().__init__(self.msg)

@shared_task(bind=True)
def create_local_seed_task(self, preset_pk, user_id, user_name):
    """
    Generates a seed in a temporary directory, moves the final zip to the
    media root, and cleans up intermediate files.
    """
    preset = Preset.objects.get(pk=preset_pk)
    final_flags = flag_processor.apply_args(preset.flags, preset.arguments)
    unique_id = str(uuid.uuid4())[:8]
    filename_base = f"{preset.preset_name.replace(' ', '_').replace('/', '-')}_{unique_id}"
    args_list = preset.arguments.split() if preset.arguments else []

    project_root = settings.BASE_DIR.parent
    seedbot2000_dir = project_root / 'seedbot2000'
    main_wc_dir = seedbot2000_dir / 'WorldsCollide'

    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)
        output_smc = temp_path / f"{filename_base}.smc"

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
        
        command = [
            "python3", str(wc_script),
            "-i", str(main_wc_dir / 'ff3.smc'),
            "-o", str(output_smc)
        ]
        command.extend(final_flags.split())

        try:
            # --- Step 1: Generate the base seed ---
            self.update_state(state='PROGRESS', meta={'status': 'Generating Seed...'})
            subprocess.run(
                command, cwd=script_dir, capture_output=True,
                encoding='utf-8', timeout=120, check=True
            )
            
            music_was_randomized = False
            jdm_type = "standard"

            # Step 2: Conditionally Randomize Music
            if 'tunes' in args_list or 'ctunes' in args_list:
                # --- NEW: Report progress before starting tunes ---
                self.update_state(state='PROGRESS', meta={'status': 'Applying Tunes...'})
                
                music_was_randomized = True
                music_log_path = temp_path / f"{filename_base}_spoiler.txt"
                
                if 'ctunes' in args_list:
                    jdm_type = "chaos"
                
                original_cwd = os.getcwd()
                try:
                    os.chdir(settings.BASE_DIR / 'johnnydmad')
                    asyncio.run(johnnydmad_webapp(
                        c=jdm_type,
                        input_smc_path=str(output_smc),
                        output_smc_path=str(output_smc),
                        spoiler_log_path=str(music_log_path)
                    ))
                finally:
                    os.chdir(original_cwd)
            
            # --- Step 3: Zip all the files ---
            self.update_state(state='PROGRESS', meta={'status': 'Packaging Seed...'})
            zip_filename = f"{filename_base}.zip"
            original_log_path = temp_path / f"{filename_base}.txt"
            zip_path = temp_path / zip_filename

            with zipfile.ZipFile(zip_path, 'w') as zf:
                zf.write(output_smc, arcname=f"{jdm_type}_{filename_base}.smc")
                if original_log_path.exists():
                    zf.write(original_log_path, arcname=f"{jdm_type}_{filename_base}.txt")
                if music_was_randomized and music_log_path.exists():
                    zf.write(music_log_path, arcname=f"{jdm_type}_{filename_base}_music_swaps.txt")
            
            # Step 4: Move the final zip file to its permanent location
            final_destination = Path(settings.MEDIA_ROOT) / zip_filename
            shutil.move(zip_path, final_destination)

            # Step 5: Log and return
            preset.gen_count += 1
            preset.save(update_fields=['gen_count'])
            share_url = f'{settings.MEDIA_URL}{zip_filename}'
            timestamp = datetime.now().strftime('%b %d %Y %H:%M:%S')
            SeedLog.objects.create(
                creator_id=user_id, creator_name=user_name,
                seed_type=preset.preset_name, share_url=share_url,
                timestamp=timestamp, server_name='WebApp'
            )
            metrics_data = {
                'creator_id': user_id, 'creator_name': user_name,
                'seed_type': preset.preset_name, 'share_url': share_url,
                'timestamp': timestamp,
            }
            write_to_gsheets(metrics_data)

            return share_url

        except Exception as e:
            log_path = settings.BASE_DIR / 'debug_task.log'
            err_msg = f"An error occurred: {str(e)}"
            with open(log_path, 'a', encoding='utf-8') as f:
                f.write(f"\n--- Task Failed: {datetime.now()} ---\n")
                traceback.print_exc(file=f)
                if isinstance(e, subprocess.CalledProcessError):
                    f.write("\n--- Subprocess STDOUT ---\n")
                    f.write(e.stdout or "N/A")
                    f.write("\n--- Subprocess STDERR ---\n")
                    f.write(e.stderr or "N/A")
                    err_msg = f"A script failed to run: {e.stderr or e.stdout}"
            self.update_state(state='FAILURE', meta={'exc_type': type(e).__name__, 'exc_message': err_msg})
            raise Ignore()