# Models (at least, User ones) should be here so Etebase can find them
import typing as t

from django.contrib.auth.models import AbstractUser
from django.db import models
from django.utils.translation import gettext_lazy as _
from django.contrib.auth.base_user import BaseUserManager
from django.core.validators import RegexValidator
from django_etebase.models import Collection

UidValidator = RegexValidator(regex=r"^[a-zA-Z0-9\-_]{20,}$", message="Not a valid UID")


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
            raise ValueError(_("The Email must be set"))
        if not username:
            raise ValueError(_("The Username must be set"))

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

    email = models.EmailField(_("email address"), unique=True)
    username = models.CharField(_("username"), max_length=150, unique=True)

    USERNAME_FIELD = "email"
    EMAIL_FIELD = "email"
    REQUIRED_FIELDS = []

    objects = UserManager()

    def __str__(self):
        return self.email


# For the limits, Null is unlimited
class Tier(models.Model):
    id: int
    name = models.CharField(max_length=50)
    stripe_flat_price_id = models.CharField(blank=True, max_length=50, null=True, unique=True)
    stripe_storage_price_id = models.CharField(blank=True, max_length=50, null=True, unique=True)
    stripe_user_price_id = models.CharField(blank=True, max_length=50, null=True, unique=True)
    stripe_collaborator_price_id = models.CharField(blank=True, max_length=50, null=True, unique=True)
    stripe_project_price_id = models.CharField(blank=True, max_length=50, null=True, unique=True)

    base_user_limit = models.IntegerField(null=True)
    base_project_limit = models.IntegerField(null=True)
    base_collaborator_limit = models.IntegerField(null=True)
    base_storage_limit = models.IntegerField(null=True)

    is_custom = models.BooleanField(null=False, default=False)
    custom_subscription_id = models.CharField(null=True, blank=True, max_length=50, unique=True)


class Team(models.Model):
    id: int
    name = models.CharField(max_length=200, default="")
    owner = models.OneToOneField(User, on_delete=models.CASCADE)
    tier = models.ForeignKey(Tier, on_delete=models.PROTECT)
    usage = models.IntegerField(verbose_name="Storage usage in MB", null=True)


# These are any addons that a user has purchased, the pricing is determined by their tier
# We generate their usage limits from their tier + any values here
class TierAddons(models.Model):
    team = models.ForeignKey(Team, on_delete=models.CASCADE)
    additional_user_count = models.IntegerField(null=True)
    additional_project_count = models.IntegerField(null=True)
    additional_collaborator_count = models.IntegerField(null=True)
    # You can't buy more storage, it's just billed
    created_date = models.DateTimeField(auto_now_add=True, blank=False, null=False)


class UserProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, primary_key=True)
    name = models.CharField(max_length=200)
    recovery_key = models.TextField(null=True)
    team = models.ForeignKey(Team, on_delete=models.CASCADE)
    email_verified = models.DateTimeField(blank=True, null=True)
    accepted_terms_and_conditions = models.DateTimeField(blank=True, null=True)
    is_collaborator = models.BooleanField(null=False, default=False)
    is_trusted_service = models.BooleanField(null=False, default=False)

    def __str__(self):
        return self.user.email


class Billing(models.Model):
    team = models.OneToOneField(Team, on_delete=models.CASCADE)
    stripe_customer_id = models.CharField(max_length=255, unique=True)
    start_date = models.DateTimeField(blank=True, null=True)
    renewal_date = models.DateTimeField(blank=True, null=True)
    trial_start = models.DateTimeField(blank=True, null=True)
    trial_end = models.DateTimeField(blank=True, null=True)
    subscription_id = models.CharField(max_length=255, blank=True)
    cancel_date = models.DateTimeField(blank=True, null=True)


class CustomBilling(models.Model):
    team = models.OneToOneField(Team, on_delete=models.CASCADE)
    start_date = models.DateTimeField(blank=True, null=True)
    renewal_date = models.DateTimeField(blank=True, null=True)
    cancel_date = models.DateTimeField(blank=True, null=True)


class Invite(models.Model):
    uid = models.CharField(db_index=True, blank=False, null=False, max_length=43, validators=[UidValidator])
    from_team = models.ForeignKey(Team, on_delete=models.CASCADE)
    email = models.EmailField(_("email address"), unique=True)
    is_collaborator = models.BooleanField(null=False, default=False)
    sent_date = models.DateTimeField(auto_now_add=True, blank=False, null=False)
    accepted_date = models.DateTimeField(blank=True, null=True)


class Recovery(models.Model):
    uid = models.CharField(
        db_index=True, blank=False, null=False, max_length=43, validators=[UidValidator], primary_key=True
    )
    user_profile = models.ForeignKey(UserProfile, on_delete=models.CASCADE)
    expiry_date = models.DateTimeField(blank=False, null=False)


class EmailVerification(models.Model):
    uid = models.CharField(
        db_index=True, blank=False, null=False, max_length=43, validators=[UidValidator], primary_key=True
    )
    user_profile = models.ForeignKey(UserProfile, on_delete=models.CASCADE)
    expiry_date = models.DateTimeField(blank=False, null=False)


PRODUCTS = (
    ("CURATE", "CURATE"),
    ("ANNOTATE", "ANNOTATE"),
    ("ALL", "ALL"),
)


class Plugin(models.Model):
    TYPE = (("Javascript", "Javascript"), ("Python", "Python"), ("AI", "AI"))

    id: int
    team = models.ForeignKey(Team, on_delete=models.CASCADE)  # cannot be edited by user
    type = models.CharField(max_length=20, choices=TYPE)  # cannot be edited by user
    url = models.URLField(blank=False, null=False, max_length=200)  # cannot be edited by user
    origin = models.ForeignKey("self", blank=True, null=True, on_delete=models.CASCADE)  # cannot be edited by user
    name = models.CharField(blank=False, null=False, max_length=50)
    description = models.CharField(blank=True, null=False, max_length=500)
    products = models.CharField(max_length=20, choices=PRODUCTS)
    enabled = models.BooleanField(null=False, default=False)
    collections = models.ManyToManyField(Collection, blank=True)
    is_public = models.BooleanField(blank=True, null=True, default=False)


class TrustedService(models.Model):
    id: int
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    plugin = models.OneToOneField(Plugin, on_delete=models.CASCADE)
    public_key = models.CharField(max_length=100, blank=True, null=True)
    encrypted_access_key = models.CharField(max_length=100, blank=True, null=True)


class UserFeedback(models.Model):
    """Model for storing users' feedback."""

    RATE_CHOICES = (
        (4, "excellent"),
        (3, "very good"),
        (2, "good"),
        (1, "fair"),
        (0, "poor"),
    )
    user = models.ForeignKey(User, null=True, on_delete=models.SET_NULL)
    rating = models.PositiveSmallIntegerField(choices=RATE_CHOICES, blank=True, null=True)
    comment = models.TextField(blank=True, max_length=500)
    date = models.DateTimeField(auto_now_add=True)


class Usage(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    date = models.DateTimeField(auto_now_add=True, blank=False, null=False)
    usage = models.IntegerField(null=False, blank=False)


UserType = User


def get_typed_user_model() -> UserType:
    from django.contrib.auth import get_user_model

    ret: t.Any = get_user_model()
    return ret
