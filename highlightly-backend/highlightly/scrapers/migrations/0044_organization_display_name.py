# Generated by Django 4.2 on 2023-06-04 21:43

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('scrapers', '0043_tournament_short_name'),
    ]

    operations = [
        migrations.AddField(
            model_name='organization',
            name='display_name',
            field=models.CharField(blank=True, max_length=128, null=True),
        ),
    ]