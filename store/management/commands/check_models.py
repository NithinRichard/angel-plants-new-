from django.core.management.base import BaseCommand
from django.apps import apps

class Command(BaseCommand):
    help = 'Check for model-related issues'

    def handle(self, *args, **options):
        try:
            # Try to get all models
            for model in apps.get_models():
                self.stdout.write(self.style.SUCCESS(f'Successfully loaded model: {model.__name__}'))
            self.stdout.write(self.style.SUCCESS('All models loaded successfully!'))
        except Exception as e:
            self.stderr.write(self.style.ERROR(f'Error loading models: {str(e)}'))
