# Generated by Django 4.2 on 2023-06-01 07:24

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('scrapers', '0040_alter_gamevod_start_datetime'),
    ]

    operations = [
        migrations.AddField(
            model_name='gamevod',
            name='process_id',
            field=models.IntegerField(blank=True, null=True),
        ),
    ]
