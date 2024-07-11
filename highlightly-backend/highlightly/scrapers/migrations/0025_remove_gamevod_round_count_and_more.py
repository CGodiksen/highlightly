# Generated by Django 4.2 on 2023-05-08 07:24

import django.core.validators
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('scrapers', '0024_gamevod_round_count'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='gamevod',
            name='round_count',
        ),
        migrations.AddField(
            model_name='gamevod',
            name='team_1_round_count',
            field=models.IntegerField(default=1, validators=[django.core.validators.MinValueValidator(0)]),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name='gamevod',
            name='team_2_round_count',
            field=models.IntegerField(default=1, validators=[django.core.validators.MinValueValidator(0)]),
            preserve_default=False,
        ),
    ]