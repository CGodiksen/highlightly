# Generated by Django 4.2 on 2023-05-28 20:16

import django.core.validators
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('videos', '0003_alter_videometadata_match'),
    ]

    operations = [
        migrations.AddField(
            model_name='videometadata',
            name='thumbnail_match_frame_time',
            field=models.IntegerField(default=1, validators=[django.core.validators.MinValueValidator(1)]),
            preserve_default=False,
        ),
    ]
