"""Project user model."""

from django.contrib.auth.models import AbstractUser
from django.db import models


# [Implementation 1]
# The custom user is created before the first migration so later relations never target auth.User.
class User(AbstractUser):
    email = models.EmailField(unique=True)

    def __str__(self) -> str:
        return self.get_full_name() or self.username
