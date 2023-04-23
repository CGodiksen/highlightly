# Generated by Django 4.2 on 2023-04-23 06:40

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('scrapers', '0017_finishedmatch_gamevod'),
    ]

    operations = [
        migrations.RenameField(
            model_name='gamevod',
            old_name='vod_filename',
            new_name='filename',
        ),
        migrations.RenameField(
            model_name='gamevod',
            old_name='vod_url',
            new_name='url',
        ),
        migrations.AddField(
            model_name='gamevod',
            name='map',
            field=models.CharField(default='', max_length=64),
            preserve_default=False,
        ),
        migrations.AlterField(
            model_name='gamevod',
            name='finished_match',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='scrapers.scheduledmatch'),
        ),
        migrations.DeleteModel(
            name='FinishedMatch',
        ),
    ]