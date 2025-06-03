from django.core.management.base import BaseCommand
from django.db import connection

class Command(BaseCommand):
    help = 'Check the database schema for the Order model'

    def handle(self, *args, **options):
        with connection.cursor() as cursor:
            # For MySQL
            cursor.execute("SHOW COLUMNS FROM store_order")
            columns = cursor.fetchall()
            
            self.stdout.write("Columns in store_order table:")
            for column in columns:
                self.stdout.write(f"- {column[0]} ({column[1]})")
                
            # Check if address2 column exists
            cursor.execute("""
                SELECT COUNT(*) 
                FROM information_schema.COLUMNS 
                WHERE TABLE_SCHEMA = DATABASE() 
                AND TABLE_NAME = 'store_order' 
                AND COLUMN_NAME = 'address2'
            """)
            address2_exists = cursor.fetchone()[0] > 0
            self.stdout.write(f"\nAddress2 column exists: {address2_exists}")
