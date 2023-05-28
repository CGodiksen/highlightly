# Generated by Django 4.2 on 2023-05-28 20:18

import django.core.validators
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('videos', '0004_videometadata_thumbnail_match_frame_time'),
    ]

    operations = [
        migrations.AlterField(
            model_name='videometadata',
            name='thumbnail_match_frame_time',
            field=models.IntegerField(blank=True, null=True, validators=[django.core.validators.MinValueValidator(1)]),
        ),
    ]
