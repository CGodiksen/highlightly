# Generated by Django 4.2 on 2023-04-18 08:53

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('scrapers', '0004_scheduledmatch_create_video_team_url'),
    ]

    operations = [
        migrations.AlterModelOptions(
            name='scheduledmatch',
            options={'verbose_name_plural': 'Scheduled matches'},
        ),
    ]
