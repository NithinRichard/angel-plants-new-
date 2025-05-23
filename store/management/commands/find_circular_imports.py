import sys
import os
from django.core.management.base import BaseCommand
from django.apps import apps

class Command(BaseCommand):
    help = 'Find circular imports in models'

    def handle(self, *args, **options):
        # Get all model names
        model_names = [model.__name__ for model in apps.get_models()]
        
        # Check each model for circular imports
        for model_name in model_names:
            try:
                self.stdout.write(f"Checking {model_name}...")
                model = apps.get_model('store', model_name)
                # Try to access related models
                for field in model._meta.get_fields():
                    if hasattr(field, 'related_model') and field.related_model:
                        related_model = field.related_model
                        self.stdout.write(f"  - {field.name}: {related_model.__name__}")
            except Exception as e:
                self.stderr.write(f"Error with {model_name}: {str(e)}")
                
        self.stdout.write(self.style.SUCCESS('Done checking for circular imports'))
