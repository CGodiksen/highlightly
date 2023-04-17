# Generated by Django 4.2 on 2023-04-17 10:09

from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
    ]

    operations = [
        migrations.CreateModel(
            name='Tournament',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('game', models.CharField(choices=[('COUNTER_STRIKE', 'Counter-Strike'), ('LEAGUE_OF_LEGENDS', 'League of Legends'), ('VALORANT', 'Valorant')], max_length=32)),
                ('name', models.CharField(max_length=128)),
                ('logo_filename', models.CharField(max_length=256)),
                ('url', models.URLField(max_length=128)),
            ],
        ),
    ]
