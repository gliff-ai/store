import typing as t

from django.contrib.auth.models import AbstractUser, UserManager as DjangoUserManager
from django.core import validators
from django.db import models
from django.utils.deconstruct import deconstructible
from django.utils.translation import gettext_lazy as _


@deconstructible
class UnicodeUsernameValidator(validators.RegexValidator):
    regex = r"^[\w.-]+\Z"
    message = _("Enter a valid username. This value may contain only letters, " "numbers, and ./-/_ characters.")
    flags = 0


class UserManager(DjangoUserManager):
    def get_by_natural_key(self, username: str):
        return self.get(**{self.model.USERNAME_FIELD + "__iexact": username})


class User(AbstractUser):
    id: int
    username_validator = UnicodeUsernameValidator()

    objects: UserManager = UserManager()

    username = models.CharField(
        _("username"),
        max_length=150,
        unique=True,
        help_text=_("Required. 150 characters or fewer. Letters, digits and ./-/_ only."),
        validators=[username_validator],
        error_messages={
            "unique": _("A user with that username already exists."),
        },
    )

    @classmethod
    def normalize_username(cls, username: str):
        return super().normalize_username(username).lower()


UserType = User


def get_typed_user_model() -> UserType:
    from django.contrib.auth import get_user_model

    ret: t.Any = get_user_model()
    return ret
