import pprint
from datetime import timezone, datetime

from django.core.management.base import BaseCommand, CommandError
from myauth.models import User

pp = pprint.PrettyPrinter(indent=2)


class Command(BaseCommand):
    help = "Enable a user account. Useful if they didn't get the email, or have now paid etc"

    def add_arguments(self, parser):
        parser.add_argument("user_name", help="Email")

    def handle(self, *args, **options):
        try:
            user = User.objects.get(email__exact=options["user_name"])
        except User.DoesNotExist:
            raise CommandError('User "%s" does not exist' % options["user_name"])

        self.stdout.write('Got user: "%s"' % user.name)

        user.is_active = True
        if not user.userprofile.email_verified:
            user.userprofile.email_verified = datetime.now(tz=timezone.utc)
        user.save()

        self.stdout.write("User enabled")
