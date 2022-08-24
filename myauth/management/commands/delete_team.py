import shutil
import pprint

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.contrib.admin.utils import NestedObjects
from myauth.models import Team, User, Collection

pp = pprint.PrettyPrinter(indent=2)


class Command(BaseCommand):
    help = (
        "Removes a team and all of the users and data related to it. Be VERY careful doing this. Soft deleting or "
        "disabling the account is probably better. "
        "This will remove users, plugins, billing info and remove the encrypted data"
    )

    def add_arguments(self, parser):
        parser.add_argument("team_id", help="Team ID")

    def handle(self, *args, **options):
        nested_object = NestedObjects("default")

        try:
            team = Team.objects.get(pk=options["team_id"])
        except Team.DoesNotExist:
            raise CommandError('Team "%s" does not exist' % options["team_id"])

        self.stdout.write('Got team: "%s"' % team.name)

        users = User.objects.filter(team=team)

        for user in users:
            nested_object.collect([user])
            pp.pprint(nested_object.nested())

            # Delete any collections owned by this user
            # If collections are ever shared across teams, don't do this!
            cols = Collection.objects.filter(owner_id=user.id)
            for col in cols:
                col.delete()

            shutil.rmtree("%s/user_%s" % (settings.MEDIA_ROOT, user.id))
            user.delete()

        team.delete()
        self.stdout.write("Team removed")
