from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [
        ('payapp', '0001_initial'),
        ('register', '0001_initial'),
        ('auth', '0012_alter_user_first_name_max_length'),
    ]
    # Keep the migration identity, but never recreate a public default credential.
    operations = []
