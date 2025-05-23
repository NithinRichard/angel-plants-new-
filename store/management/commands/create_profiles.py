from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from django.apps import apps

User = get_user_model()
Profile = apps.get_model('store', 'Profile')

class Command(BaseCommand):
    help = 'Create profiles for existing users'

    def handle(self, *args, **options):
        users_without_profile = User.objects.filter(profile=None)
        for user in users_without_profile:
            Profile.objects.create(user=user)
            self.stdout.write(self.style.SUCCESS(f'Successfully created profile for {user.username}'))
