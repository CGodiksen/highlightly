# Generated by Django 4.2 on 2023-05-04 19:16

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('highlights', '0002_alter_highlight_game_vod'),
    ]

    operations = [
        migrations.AddField(
            model_name='highlight',
            name='value',
            field=models.FloatField(default=0),
            preserve_default=False,
        ),
    ]
