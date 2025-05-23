""
Django management command to optimize database performance.
"""
import logging
from django.core.management.base import BaseCommand
from django.db import connection, transaction
from django.conf import settings

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = 'Optimize database tables for better performance'

    def add_arguments(self, parser):
        parser.add_argument(
            '--analyze',
            action='store_true',
            help='Run ANALYZE on tables to update statistics',
        )
        parser.add_argument(
            '--vacuum',
            action='store_true',
            help='Run VACUUM on tables (PostgreSQL only)',
        )
        parser.add_argument(
            '--reindex',
            action='store_true',
            help='Rebuild indexes',
        )
        parser.add_argument(
            '--all',
            action='store_true',
            help='Run all optimizations',
        )

    def handle(self, *args, **options):
        vendor = connection.vendor
        
        if options['all']:
            options.update({
                'analyze': True,
                'vacuum': True,
                'reindex': True,
            })
        
        if not any([options['analyze'], options['vacuum'], options['reindex']]):
            self.stdout.write(self.style.WARNING('No optimization actions specified. Use --help for options.'))
            return
        
        self.stdout.write(f'Optimizing {vendor.upper()} database...')
        
        with connection.cursor() as cursor:
            if vendor == 'postgresql':
                self.optimize_postgresql(cursor, options)
            elif vendor == 'mysql':
                self.optimize_mysql(cursor, options)
            elif vendor == 'sqlite':
                self.optimize_sqlite(cursor, options)
            else:
                self.stdout.write(self.style.WARNING(f'Unsupported database vendor: {vendor}'))
                return
        
        self.stdout.write(self.style.SUCCESS('Database optimization complete'))
    
    def optimize_postgresql(self, cursor, options):
        """Optimize PostgreSQL database."""
        if options['vacuum']:
            self.stdout.write('Running VACUUM...')
            cursor.execute('VACUUM')
            self.stdout.write(self.style.SUCCESS('VACUUM completed'))
        
        if options['analyze']:
            self.stdout.write('Running ANALYZE...')
            cursor.execute('ANALYZE')
            self.stdout.write(self.style.SUCCESS('ANALYZE completed'))
        
        if options['reindex']:
            self.stdout.write('Rebuilding indexes...')
            cursor.execute("""
                SELECT tablename 
                FROM pg_tables 
                WHERE schemaname = 'public';
            """)
            tables = [row[0] for row in cursor.fetchall()]
            
            for table in tables:
                cursor.execute(f'REINDEX TABLE {table}')
                self.stdout.write(f'  Reindexed {table}')
            
            self.stdout.write(self.style.SUCCESS('All indexes rebuilt'))
    
    def optimize_mysql(self, cursor, options):
        """Optimize MySQL database."""
        if options['analyze']:
            self.stdout.write('Running ANALYZE TABLE...')
            cursor.execute('SHOW TABLES')
            tables = [row[0] for row in cursor.fetchall()]
            
            for table in tables:
                cursor.execute(f'ANALYZE TABLE {table}')
                result = cursor.fetchone()
                self.stdout.write(f'  Analyzed {table}: {result}')
            
            self.stdout.write(self.style.SUCCESS('ANALYZE completed'))
        
        if options['reindex']:
            self.stdout.write('Optimizing tables (this may take a while)...')
            cursor.execute('SHOW TABLES')
            tables = [row[0] for row in cursor.fetchall()]
            
            for table in tables:
                cursor.execute(f'OPTIMIZE TABLE {table}')
                result = cursor.fetchone()
                self.stdout.write(f'  Optimized {table}: {result}')
            
            self.stdout.write(self.style.SUCCESS('Table optimization completed'))
    
    def optimize_sqlite(self, cursor, options):
        """Optimize SQLite database."""
        if options['vacuum']:
            self.stdout.write('Running VACUUM...')
            cursor.execute('VACUUM')
            self.stdout.write(self.style.SUCCESS('VACUUM completed'))
        
        if options['analyze']:
            self.stdout.write('Running ANALYZE...')
            cursor.execute('ANALYZE')
            self.stdout.write(self.style.SUCCESS('ANALYZE completed'))
        
        if options['reindex']:
            self.stdout.write('Rebuilding indexes...')
            cursor.execute('REINDEX')
            self.stdout.write(self.style.SUCCESS('All indexes rebuilt'))
