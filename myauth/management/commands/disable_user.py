import pprint

from django.core.management.base import BaseCommand, CommandError
from myauth.models import Team, User, Collection

pp = pprint.PrettyPrinter(indent=2)


class Command(BaseCommand):
    help = "Disable a single user account. We don't remove any data (mainly in case Collections are shared elsewhere)"

    def add_arguments(self, parser):
        parser.add_argument("user_name", help="Email")

    def handle(self, *args, **options):
        try:
            user = User.objects.get(email__exact=options["user_name"])
        except User.DoesNotExist:
            raise CommandError('User "%s" does not exist' % options["user_name"])

        self.stdout.write('Got user: "%s"' % user.name)

        user.is_active = False
        user.save()

        self.stdout.write("User disabled")
