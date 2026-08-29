"""Account forms."""

from django.contrib.auth.forms import UserCreationForm

from .models import User


# [Implementation 9]
# Registration uses Django's password validation and only exposes fields a visitor may set.
class SignUpForm(UserCreationForm):
    class Meta(UserCreationForm.Meta):
        model = User
        fields = ("username", "email")
