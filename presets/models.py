from django.db import models

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