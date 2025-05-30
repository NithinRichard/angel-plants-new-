from django.db import migrations

class Migration(migrations.Migration):
    """
    This migration marks the 'total' field as already applied.
    The 'total' column already exists in the database, so we just need to mark this migration as applied.
    """
    
    dependencies = [
        ('store', '0001_initial'),
    ]

    operations = [
        # This is intentionally left empty as the column already exists
    ]
    
    # This tells Django to mark this migration as applied without running any SQL
    run_before = [
        ('store', '0002_add_total_to_cart'),
    ]
