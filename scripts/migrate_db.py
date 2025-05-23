"""
Database migration and schema management script.
"""
import os
import sys
import logging
import argparse
from pathlib import Path
from typing import List, Dict, Any, Optional

import django
from django.conf import settings
from django.db import connection, connections, DEFAULT_DB_ALIAS
from django.core.management import call_command

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('migration.log')
    ]
)
logger = logging.getLogger(__name__)

class DatabaseMigrator:
    """Handle database migrations and schema changes."""
    
    def __init__(self, database: str = 'default'):
        """Initialize with database connection."""
        self.database = database
        self.connection = connections[database]
        self.vendor = self.connection.vendor
    
    def create_migration(self, app_label: str = '', name: str = 'auto', dry_run: bool = False) -> bool:
        """Create new migrations for an app."""
        logger.info(f'Creating migrations for {app_label or "all apps"}...')
        try:
            call_command(
                'makemigrations',
                app_label or '',
                name=name if name != 'auto' else None,
                dry_run=dry_run,
                no_input=True,
                verbosity=1,
                database=self.database
            )
            return True
        except Exception as e:
            logger.error(f'Error creating migrations: {e}')
            return False
    
    def apply_migrations(self, app_label: str = None, migration: str = None, fake: bool = False) -> bool:
        """Apply pending migrations."""
        logger.info('Applying migrations...')
        try:
            args = []
            if app_label:
                args.append(app_label)
                if migration:
                    args.append(migration)
            
            call_command(
                'migrate',
                *args,
                database=self.database,
                fake=fake,
                verbosity=1,
                no_color=False,
            )
            return True
        except Exception as e:
            logger.error(f'Error applying migrations: {e}')
            return False
    
    def show_migrations(self, app_label: str = None) -> List[Dict[str, Any]]:
        """Show all migrations and their status."""
        logger.info('Checking migration status...')
        migrations = []
        
        from django.db.migrations.loader import MigrationLoader
        loader = MigrationLoader(connection=self.connection)
        
        # Get applied migrations
        applied = set(loader.applied_migrations)
        
        # Get all migrations
        for app_name, app_migrations in loader.disk_migrations.items():
            if app_label and app_label != app_name:
                continue
                
            for migration_name, migration in app_migrations.items():
                is_applied = (app_name, migration_name) in applied
                migrations.append({
                    'app': app_name,
                    'name': migration_name,
                    'applied': is_applied,
                    'migration': migration
                })
        
        return migrations
    
    def check_migration_conflicts(self) -> List[Dict[str, Any]]:
        """Check for migration conflicts."""
        logger.info('Checking for migration conflicts...')
        conflicts = []
        
        from django.db.migrations.loader import MigrationLoader
        loader = MigrationLoader(connection=self.connection)
        
        # Check for conflicts
        for app_label, app_migrations in loader.disk_migrations.items():
            for migration_name, migration in app_migrations.items():
                for dependency in migration.dependencies:
                    dep_app, dep_name = dependency
                    if dep_app not in loader.disk_migrations:
                        conflicts.append({
                            'app': app_label,
                            'migration': migration_name,
                            'issue': f'Dependency {dep_app} not found',
                            'severity': 'error'
                        })
        
        return conflicts
    
    def squash_migrations(self, app_label: str, target: str = None) -> bool:
        """Squash migrations for an app."""
        logger.info(f'Squashing migrations for {app_label}...')
        try:
            args = [app_label]
            if target:
                args.append(target)
                
            call_command(
                'squashmigrations',
                *args,
                no_input=True,
                verbosity=1,
                database=self.database
            )
            return True
        except Exception as e:
            logger.error(f'Error squashing migrations: {e}')
            return False
    
    def reset_migrations(self, app_label: str) -> bool:
        """Reset migrations for an app (DANGEROUS - use with caution)."""
        logger.warning(f'Resetting migrations for {app_label} - THIS WILL DELETE MIGRATION HISTORY')
        confirm = input('Are you sure you want to continue? (yes/no): ')
        if confirm.lower() != 'yes':
            logger.info('Operation cancelled')
            return False
            
        try:
            # Delete migration files
            migrations_dir = Path(settings.BASE_DIR) / app_label / 'migrations'
            if migrations_dir.exists():
                for f in migrations_dir.glob('*.py'):
                    if f.name != '__init__.py':
                        f.unlink()
            
            # Reset database
            with connection.cursor() as cursor:
                cursor.execute(
                    "DELETE FROM django_migrations WHERE app = %s", 
                    [app_label]
                )
            
            # Create new initial migration
            return self.create_migration(app_label, 'initial')
            
        except Exception as e:
            logger.error(f'Error resetting migrations: {e}')
            return False

def main():
    """Main function for command-line usage."""
    parser = argparse.ArgumentParser(description='Manage database migrations.')
    subparsers = parser.add_subparsers(dest='command', help='Command to run')
    
    # Create migrations command
    create_parser = subparsers.add_parser('create', help='Create new migrations')
    create_parser.add_argument('app_label', nargs='?', default='', help='App label')
    create_parser.add_argument('--name', default='auto', help='Migration name')
    create_parser.add_argument('--dry-run', action='store_true', help='Dry run')
    
    # Apply migrations command
    apply_parser = subparsers.add_parser('apply', help='Apply migrations')
    apply_parser.add_argument('app_label', nargs='?', help='App label')
    apply_parser.add_argument('migration', nargs='?', help='Migration name')
    apply_parser.add_argument('--fake', action='store_true', help='Mark as run without running')
    
    # Show migrations command
    show_parser = subparsers.add_parser('show', help='Show migrations')
    show_parser.add_argument('app_label', nargs='?', help='App label')
    
    # Check conflicts command
    conflicts_parser = subparsers.add_parser('check', help='Check for migration conflicts')
    
    # Squash migrations command
    squash_parser = subparsers.add_parser('squash', help='Squash migrations')
    squash_parser.add_argument('app_label', help='App label')
    squash_parser.add_argument('--target', help='Target migration')
    
    # Reset migrations command
    reset_parser = subparsers.add_parser('reset', help='Reset migrations (DANGEROUS)')
    reset_parser.add_argument('app_label', help='App label')
    
    # Common arguments
    for p in [create_parser, apply_parser, show_parser, conflicts_parser, squash_parser, reset_parser]:n        p.add_argument('--database', default='default', help='Database connection name')
    
    args = parser.parse_args()
    
    # Setup Django environment
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'angels_plants.settings')
    django.setup()
    
    migrator = DatabaseMigrator(database=args.database)
    
    if args.command == 'create':
        migrator.create_migration(args.app_label, args.name, args.dry_run)
    elif args.command == 'apply':
        migrator.apply_migrations(args.app_label, args.migration, args.fake)
    elif args.command == 'show':
        migrations = migrator.show_migrations(args.app_label)
        for m in migrations:
            status = '✓' if m['applied'] else '✗'
            print(f"{status} {m['app']} {m['name']}")
    elif args.command == 'check':
        conflicts = migrator.check_migration_conflicts()
        if conflicts:
            print(f"Found {len(conflicts)} migration conflicts:")
            for c in conflicts:
                print(f"- {c['app']}.{c['migration']}: {c['issue']}")
            sys.exit(1)
        else:
            print("No migration conflicts found.")
    elif args.command == 'squash':
        migrator.squash_migrations(args.app_label, getattr(args, 'target', None))
    elif args.command == 'reset':
        migrator.reset_migrations(args.app_label)
    else:
        parser.print_help()

if __name__ == '__main__':
    main()
