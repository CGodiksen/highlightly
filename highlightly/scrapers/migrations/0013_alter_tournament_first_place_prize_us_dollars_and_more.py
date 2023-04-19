# Generated by Django 4.2 on 2023-04-19 19:24

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('scrapers', '0012_tournament_end_date_and_more'),
    ]

    operations = [
        migrations.AlterField(
            model_name='tournament',
            name='first_place_prize_us_dollars',
            field=models.CharField(blank=True, max_length=32, null=True),
        ),
        migrations.AlterField(
            model_name='tournament',
            name='prize_pool_us_dollars',
            field=models.CharField(blank=True, max_length=32, null=True),
        ),
    ]
