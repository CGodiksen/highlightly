# Generated by Django 4.2 on 2023-06-01 08:27

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('scrapers', '0042_match_stream_url'),
    ]

    operations = [
        migrations.AddField(
            model_name='tournament',
            name='short_name',
            field=models.CharField(blank=True, max_length=32, null=True),
        ),
    ]