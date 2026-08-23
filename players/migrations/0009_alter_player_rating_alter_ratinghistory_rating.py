import django.core.validators
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("players", "0008_match_match_scores_not_tied_and_more"),
    ]

    operations = [
        migrations.AlterField(
            model_name="player",
            name="rating",
            field=models.FloatField(
                default=1200,
                validators=[django.core.validators.MinValueValidator(100)],
            ),
        ),
        migrations.AlterField(
            model_name="ratinghistory",
            name="rating",
            field=models.FloatField(),
        ),
    ]
