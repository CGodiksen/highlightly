# Generated by Django 4.2 on 2023-04-23 06:50

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('videos', '0002_remove_videometadata_scheduled_match_and_more'),
        ('scrapers', '0019_match_remove_scheduledmatch_team_1_and_more'),
    ]

    operations = [
        migrations.DeleteModel(
            name='ScheduledMatch',
        ),
        migrations.AddField(
            model_name='match',
            name='team_1',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='team_1_matches', to='scrapers.team'),
        ),
        migrations.AddField(
            model_name='match',
            name='team_2',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='team_2_matches', to='scrapers.team'),
        ),
        migrations.AddField(
            model_name='match',
            name='tournament',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='scrapers.tournament'),
        ),
        migrations.AddField(
            model_name='gamevod',
            name='match',
            field=models.ForeignKey(default='', on_delete=django.db.models.deletion.CASCADE, to='scrapers.match'),
            preserve_default=False,
        ),
    ]
