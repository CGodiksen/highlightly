# Generated by Django 4.2 on 2023-04-17 10:33

import django.core.validators
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('scrapers', '0002_team'),
    ]

    operations = [
        migrations.CreateModel(
            name='ScheduledMatch',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('type', models.CharField(choices=[('BEST_OF_1', 'Best of 1'), ('BEST_OF_3', 'Best of 3'), ('BEST_OF_5', 'Best of 5')], max_length=16)),
                ('tournament_context', models.CharField(max_length=64)),
                ('tier', models.IntegerField(validators=[django.core.validators.MinValueValidator(1), django.core.validators.MaxValueValidator(5)])),
                ('url', models.URLField(max_length=128)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('start_time', models.DateTimeField()),
                ('estimated_end_time', models.DateTimeField()),
                ('finished', models.BooleanField(default=False)),
                ('team_1', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='scheduled_team_1_matches', to='scrapers.team')),
                ('team_2', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='scheduled_team_2_matches', to='scrapers.team')),
                ('tournament', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='scrapers.tournament')),
            ],
        ),
    ]