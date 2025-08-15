from django.db import models
from django.db.models.signals import post_delete
from django.dispatch import receiver              

class Preset(models.Model):
    # It's best to explicitly define a primary key. Since `preset_name` is likely unique,
    # we'll use it. If it's not unique, we may need to adjust this.
    preset_name = models.CharField(max_length=255, primary_key=True)
    
    # Discord IDs are very large numbers, so BigIntegerField is safer than IntegerField.
    creator_id = models.BigIntegerField() 
    
    creator_name = models.CharField(max_length=255)
    
    # The DB stores this as text, so we'll map it to a CharField in Django
    # to avoid data type errors.
    created_at = models.CharField(max_length=255)
    
    # TextField is for longer, potentially multi-line text.
    # We'll allow these to be blank.
    flags = models.TextField(blank=True, null=True)
    description = models.TextField(blank=True, null=True)
    arguments = models.TextField(blank=True, null=True)
    
    # BooleanField is perfect for integer columns that act as flags (0 or 1).
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