from django.core.management.base import BaseCommand
from django.apps import apps

class Command(BaseCommand):
    help = 'Check for model-related issues'

    def handle(self, *args, **options):
        try:
            # Get all models
            all_models = apps.get_models()
            self.stdout.write(self.style.SUCCESS(f'Found {len(all_models)} models'))
            
            # Print each model and its fields
            for model in all_models:
                self.stdout.write(f'\nModel: {model.__name__}')
                self.stdout.write(f'App: {model._meta.app_label}')
                self.stdout.write('Fields:')
                for field in model._meta.get_fields():
                    self.stdout.write(f'  - {field.name}: {field.get_internal_type()}')
            
            self.stdout.write(self.style.SUCCESS('All models loaded successfully!'))
            
        except Exception as e:
            self.stderr.write(self.style.ERROR(f'Error loading models: {str(e)}'))
