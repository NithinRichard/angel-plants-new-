from django.db import migrations, models

class Migration(migrations.Migration):

    dependencies = [
        ('store', '0008_add_total_field_to_cart'),
    ]

    operations = [
        migrations.RunSQL(
            """
            SET @dbname = DATABASE();
            SET @tablename = 'store_cart';
            SET @columnname = 'total';
            SET @preparedStatement = (SELECT IF(
              NOT EXISTS (
                  SELECT * FROM INFORMATION_SCHEMA.COLUMNS
                  WHERE (table_schema = @dbname)
                    AND (table_name = @tablename)
                    AND (column_name = @columnname)
              ),
              'ALTER TABLE store_cart ADD COLUMN total DECIMAL(10,2) NOT NULL DEFAULT 0;',
              'SELECT 1;'
            ));
            PREPARE alterIfNotExists FROM @preparedStatement;
            EXECUTE alterIfNotExists;
            DEALLOCATE PREPARE alterIfNotExists;
            """,
            # No reverse SQL needed as this is a safe operation
            reverse_sql="""
            -- No need to drop the column in reverse as this is a safe add
            SELECT 1;
            """
        ),
    ]
