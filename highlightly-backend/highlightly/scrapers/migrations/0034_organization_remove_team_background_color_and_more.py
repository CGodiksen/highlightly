# Generated by Django 4.2 on 2023-05-17 15:46

import colorfield.fields
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('scrapers', '0033_alter_gamevod_game_start_offset'),
    ]

    operations = [
        migrations.CreateModel(
            name='Organization',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=128)),
                ('logo_filename', models.CharField(blank=True, max_length=256, null=True)),
                ('background_color', colorfield.fields.ColorField(blank=True, default=None, image_field=None, max_length=18, null=True, samples=None)),
            ],
        ),
        migrations.RemoveField(
            model_name='team',
            name='background_color',
        ),
        migrations.RemoveField(
            model_name='team',
            name='logo_filename',
        ),
        migrations.RemoveField(
            model_name='team',
            name='name',
        ),
        migrations.AddField(
            model_name='team',
            name='organization',
            field=models.ForeignKey(default=1, on_delete=django.db.models.deletion.CASCADE, related_name='teams', to='scrapers.organization'),
            preserve_default=False,
        ),
    ]
