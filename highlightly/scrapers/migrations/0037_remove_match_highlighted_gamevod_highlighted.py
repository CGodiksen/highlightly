# Generated by Django 4.2 on 2023-05-25 21:56

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('scrapers', '0036_remove_gamevod_highlighted'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='match',
            name='highlighted',
        ),
        migrations.AddField(
            model_name='gamevod',
            name='highlighted',
            field=models.BooleanField(default=False),
        ),
    ]