import os
import django
from django.db import connection

# Set up Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'angels_plants.settings')
django.setup()

def check_table_exists(table_name):
    """Check if a table exists in the database."""
    with connection.cursor() as cursor:
        cursor.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name=%s",
            [table_name]
        )
        return cursor.fetchone() is not None

def get_table_schema(table_name):
    """Get the schema of a table."""
    with connection.cursor() as cursor:
        cursor.execute(f"PRAGMA table_info({table_name})")
        columns = cursor.fetchall()
        return columns

# Check if the wishlist table exists
table_name = 'store_wishlist'
if check_table_exists(table_name):
    print(f"Table '{table_name}' exists.")
    print("\nTable schema:")
    schema = get_table_schema(table_name)
    for column in schema:
        print(f"Column: {column[1]}, Type: {column[2]}, Nullable: {column[3]}, Default: {column[4]}")
else:
    print(f"Table '{table_name}' does not exist.")

# Check for any pending migrations
from django.db.migrations.executor import MigrationExecutor
from django.db import connections

print("\nChecking for pending migrations:")
for db in connections:
    connection = connections[db]
    connection.prepare_database()
    executor = MigrationExecutor(connection)
    plan = executor.migration_plan(executor.loader.graph.leaf_nodes())
    if plan:
        print(f"Pending migrations for {db}:")
        for migration, _ in plan:
            print(f"  {migration.app_label}.{migration.name}")
    else:
        print(f"No pending migrations for {db}.")
