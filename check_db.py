import os
import django
from django.db import connection

def check_database():
    # Set up Django
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'angels_plants.settings')
    django.setup()
    
    # Check if we can connect to the database
    with connection.cursor() as cursor:
        # List all tables
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
        tables = cursor.fetchall()
        print("\nTables in database:")
        for table in tables:
            print(f"- {table[0]}")
        
        # Check if auth_user table exists
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='auth_user';")
        if cursor.fetchone():
            print("\n✅ auth_user table exists")
            
            # Count users
            cursor.execute("SELECT COUNT(*) FROM auth_user;")
            count = cursor.fetchone()[0]
            print(f"Number of users: {count}")
            
            # List users
            cursor.execute("SELECT id, username, email FROM auth_user;")
            print("\nUsers:")
            for user in cursor.fetchall():
                print(f"- ID: {user[0]}, Username: {user[1]}, Email: {user[2]}")
        else:
            print("\n❌ auth_user table does not exist")

if __name__ == "__main__":
    check_database()
