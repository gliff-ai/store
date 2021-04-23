import typing as t

from django.contrib.auth.models import AbstractUser
from django.db import models
from django.utils.translation import gettext_lazy as _
from django.contrib.auth.base_user import BaseUserManager


class UserManager(BaseUserManager):
    """
    Custom user model manager with email. We also have username to support etebase, BUT we set this to equal the email
    and ignore whatever username was sent.
    """
    def create_user(self, username, email, **extra_fields):
        """
        Create and save a User with the given email and password.
        """
        if not email:
            raise ValueError(_('The Email must be set'))
        if not username:
            raise ValueError(_('The Username must be set'))

        user = self.model(email=self.normalize_email(email), username=email)

        user.set_unusable_password()  # They don't need a password as etebase will auth them

        user.save()
        return user


class User(AbstractUser):
    """
    We remove the first and last name fields, as we store this info in the user profile
    """
    id: int

    first_name = None
    last_name = None

    email = models.EmailField(_('email address'), unique=True)
    username = models.CharField(_('username'), max_length=150, unique=True)

    USERNAME_FIELD = 'email'
    EMAIL_FIELD = 'email'
    REQUIRED_FIELDS = []

    objects = UserManager()

    def __str__(self):
        return self.email


class Team(models.Model):
    id: int

    # Protect means you can't delete an owner, remove the team first!
    owner = models.OneToOneField(User, on_delete=models.PROTECT)


class UserProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, primary_key=True)
    first_name = models.CharField(max_length=100)
    last_name = models.CharField(max_length=100)
    recovery_key = models.BinaryField(editable=True, blank=False, null=False) #  The users encrypted key
    team = models.ForeignKey(Team, on_delete=models.RESTRICT)

    def __str__(self):
        return self.user.email


# Having this as a model lets us easily add and change tiers
class Tier(models.Model):
    id: int
    name = models.CharField(max_length=50)
    stripe_plan_id = models.CharField(max_length=25, blank=True, null=True, unique=True)  # This may not need to be defined here


class Billing(models.Model):
    team = models.OneToOneField(Team, on_delete=models.CASCADE)

    stripe_customer_id = models.CharField(max_length=255, unique=True)
    stripe_plan_id = models.CharField(max_length=25, blank=True)
    stripe_state = models.CharField(max_length=255)
    setup_intent_id = models.CharField(max_length=255)
    setup_intent_secret = models.CharField(max_length=255)
    billing_email = models.CharField(max_length=255)
    coupon = models.CharField(max_length=255, blank=True)
    start_date = models.TimeField(blank=True, null=True)
    renewal_date = models.TimeField( blank=True, null=True)
    subscription_id = models.CharField(max_length=255, blank=True)
    cancel_date = models.TimeField(blank=True, null=True)


UserType = User


def get_typed_user_model() -> UserType:
    from django.contrib.auth import get_user_model

    ret: t.Any = get_user_model()
    return ret

