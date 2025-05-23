"""
Test database setup and configuration.
"""
import os
import sys
import django
from django.test import TestCase, override_settings, TransactionTestCase
from django.conf import settings
from django.db import connection, connections
from django.db.migrations.executor import MigrationExecutor

# Print Python and Django versions for debugging
print("\nPython version:", sys.version)
print("Django version:", django.get_version())
print("Current working directory:", os.getcwd())
print("Python path:", sys.path)

class DatabaseSetupTest(TestCase):
    """Test database setup and configuration."""
    
    def test_database_configuration(self):
        """Test that the database is configured correctly for tests."""
        # Print database configuration for debugging
        print("\nDatabase configuration:")
        print(f"Database name: {connection.settings_dict['NAME']}")
        print(f"Database engine: {connection.settings_dict['ENGINE']}")
        
        # Check if we're using the test database
        db_name = connection.settings_dict['NAME']
        is_test_db = (
            'test_' in db_name or 
            db_name == ':memory:' or 
            'memorydb' in db_name or
            db_name.startswith('file:memorydb_')
        )
        print(f"Database name: {db_name}")
        print(f"Is test database: {is_test_db}")
        self.assertTrue(is_test_db, f"Not using a test database. Database name: {db_name}")
        
        # Check if migrations have been applied
        executor = MigrationExecutor(connection)
        plan = executor.migration_plan(executor.loader.graph.leaf_nodes())
        print(f"Unapplied migrations: {plan}")
        self.assertEqual(plan, [], "There are unapplied migrations")
    
    def test_database_tables_exist(self):
        """Test that required database tables exist."""
        with connection.cursor() as cursor:
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
            tables = [row[0].lower() for row in cursor.fetchall()]  # Convert to lowercase for case-insensitive comparison
            
        print("\nFound tables:", tables)
            
        # Check for required tables (using lowercase for case-insensitive comparison)
        required_tables = [
            'auth_user',
            'auth_group',
            'auth_permission',
            'django_content_type',
            'django_session',  # Note: Changed from django_sessions to django_session
            'store_order',
            'store_product',
            'store_category',
        ]
        
        missing_tables = [table for table in required_tables if table not in tables]
        print("Missing tables:", missing_tables)
        
        self.assertEqual(len(missing_tables), 0, f"Missing tables: {missing_tables}")
    
    def test_database_connection(self):
        """Test that we can connect to the database and run a simple query."""
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
            result = cursor.fetchone()
            self.assertEqual(result, (1,), "Failed to execute a simple query")
