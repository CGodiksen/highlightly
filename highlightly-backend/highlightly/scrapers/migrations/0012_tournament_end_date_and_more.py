# Generated by Django 4.2 on 2023-04-19 10:03

import django.core.validators
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('scrapers', '0011_alter_team_nationality_alter_team_ranking'),
    ]

    operations = [
        migrations.AddField(
            model_name='tournament',
            name='end_date',
            field=models.DateField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='tournament',
            name='first_place_prize_us_dollars',
            field=models.IntegerField(blank=True, null=True, validators=[django.core.validators.MinValueValidator(1)]),
        ),
        migrations.AddField(
            model_name='tournament',
            name='location',
            field=models.CharField(blank=True, max_length=128, null=True),
        ),
        migrations.AddField(
            model_name='tournament',
            name='prize_pool_us_dollars',
            field=models.IntegerField(blank=True, null=True, validators=[django.core.validators.MinValueValidator(1)]),
        ),
        migrations.AddField(
            model_name='tournament',
            name='start_date',
            field=models.DateField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='tournament',
            name='tier',
            field=models.IntegerField(blank=True, null=True, validators=[django.core.validators.MinValueValidator(1), django.core.validators.MaxValueValidator(5)]),
        ),
        migrations.AddField(
            model_name='tournament',
            name='type',
            field=models.CharField(blank=True, choices=[('OFFLINE', 'Offline'), ('ONLINE', 'Online')], max_length=16, null=True),
        ),
    ]
