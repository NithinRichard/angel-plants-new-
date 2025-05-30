from django.db import migrations

class Migration(migrations.Migration):

    dependencies = [
        ('store', '0009_safely_add_total_field'),
    ]

    operations = [
        migrations.RunSQL(
            """
            -- First, drop the procedure if it exists to avoid errors
            DROP PROCEDURE IF EXISTS add_total_column_if_not_exists;
            
            -- Create a procedure to safely add the column
            DELIMITER //
            CREATE PROCEDURE add_total_column_if_not_exists()
            BEGIN
                DECLARE CONTINUE HANDLER FOR 1060 DO BEGIN END;
                ALTER TABLE store_cart ADD COLUMN total DECIMAL(10,2) NOT NULL DEFAULT 0;
            END //
            DELIMITER ;
            
            -- Call the procedure
            CALL add_total_column_if_not_exists();
            
            -- Clean up by dropping the procedure
            DROP PROCEDURE IF EXISTS add_total_column_if_not_exists;
            """,
            # No reverse SQL needed as this is a safe operation
            reverse_sql="""
            -- No need to drop the column in reverse as this is a safe add
            SELECT 1;
            """
        ),
    ]
