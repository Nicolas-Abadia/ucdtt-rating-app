# Written by hand on 2026-09-03 (no execute tool available for
# makemigrations). Matches the migration makemigrations would produce for
# the two new Player fields, so makemigrations --check stays clean.
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("players", "0009_alter_player_rating_alter_ratinghistory_rating"),
    ]

    operations = [
        migrations.AddField(
            model_name="player",
            name="style",
            field=models.CharField(
                blank=True,
                choices=[
                    ("offensive", "Offensive"),
                    ("all-round", "All-round"),
                    ("defensive", "Defensive"),
                ],
                default="",
                max_length=20,
            ),
        ),
        migrations.AddField(
            model_name="player",
            name="grip",
            field=models.CharField(
                blank=True,
                choices=[
                    ("shakehand", "Shakehand"),
                    ("penhold", "Penhold"),
                ],
                default="",
                max_length=20,
            ),
        ),
    ]
