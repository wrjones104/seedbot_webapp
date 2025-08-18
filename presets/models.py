from django.db import models
from django.db.models.signals import post_delete
from django.dispatch import receiver

class Preset(models.Model):
    preset_name = models.CharField(max_length=255, primary_key=True)
    creator_id = models.BigIntegerField() 
    creator_name = models.CharField(max_length=255)
    created_at = models.CharField(max_length=255)
    flags = models.TextField(blank=True, null=True)
    description = models.TextField(blank=True, null=True)
    arguments = models.TextField(blank=True, null=True)
    official = models.BooleanField()
    hidden = models.BooleanField()
    gen_count = models.IntegerField(default=0)

    class Meta:
        managed = False
        db_table = 'presets'

    def __str__(self):
        return self.preset_name
    
class UserPermission(models.Model):
    user_id = models.BigIntegerField(primary_key=True)
    bot_admin = models.IntegerField()
    git_user = models.IntegerField()
    race_admin = models.IntegerField()

    class Meta:
        managed = False
        db_table = 'users'

    def __str__(self):
        return str(self.user_id)
    
class FeaturedPreset(models.Model):
    preset_name = models.CharField(max_length=255, primary_key=True)
    featured_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.preset_name

# --- NEW MODEL MAPPED TO EXISTING TABLE ---
class SeedLog(models.Model):
    # This model maps to the existing 'seedlist' table in seeDBot.sqlite
    creator_id = models.BigIntegerField()
    creator_name = models.TextField()
    seed_type = models.TextField()
    share_url = models.TextField(blank=True, null=True)
    timestamp = models.TextField(primary_key=True)
    server_name = models.TextField(blank=True, null=True)
    server_id = models.BigIntegerField(blank=True, null=True)
    channel_name = models.TextField(blank=True, null=True)
    channel_id = models.BigIntegerField(blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'seedlist'

@receiver(post_delete, sender=Preset)
def delete_featured_preset_on_preset_delete(sender, instance, **kwargs):
    """
    When a Preset is deleted, this signal finds and deletes the
    corresponding FeaturedPreset entry, if one exists.
    """
    try:
        FeaturedPreset.objects.filter(preset_name=instance.pk).delete()
        print(f"Cleaned up featured entry for deleted preset: {instance.pk}")
    except Exception as e:
        print(f"Error during featured preset cleanup: {e}")