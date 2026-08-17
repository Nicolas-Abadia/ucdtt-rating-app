from django.core.validators import MinValueValidator
from django.db import models

# Create your models here.


class Player(models.Model):
    name = models.CharField(max_length=200)
    rating = models.IntegerField(default=1200, validators=[MinValueValidator(100)])
    created_date = models.DateTimeField("created date", auto_now_add=True)

    def __str__(self):
        return self.name
