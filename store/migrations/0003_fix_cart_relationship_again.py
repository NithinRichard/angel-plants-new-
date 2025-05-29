from django.db import migrations, models

class Migration(migrations.Migration):

    dependencies = [
        ('store', '0002_fix_cart_relationship'),
    ]

    operations = [
        # Remove the old cart_id column if it exists
        migrations.RunSQL(
            # MySQL doesn't support DROP COLUMN IF EXISTS directly
            """
            SET @dbname = DATABASE();
            SET @tablename = 'store_order';
            SET @columnname = 'cart_id';
            SET @preparedStatement = (SELECT IF(
                EXISTS(
                    SELECT * FROM INFORMATION_SCHEMA.COLUMNS
                    WHERE
                        (table_schema = @dbname)
                        AND (table_name = @tablename)
                        AND (column_name = @columnname)
                ),
                "ALTER TABLE store_order DROP COLUMN cart_id",
                "SELECT 1"
            ));
            PREPARE alterIfExists FROM @preparedStatement;
            EXECUTE alterIfExists;
            DEALLOCATE PREPARE alterIfExists;
            """,
            # Reverse SQL (not always possible to reverse a DROP COLUMN)
            """
            -- This is a no-op since we can't reliably recreate the column
            -- with the correct data
            SELECT 1;
            """
        ),
        # Make sure the cart field is properly set up
        migrations.AlterField(
            model_name='order',
            name='cart',
            field=models.OneToOneField(
                blank=True,
                null=True,
                on_delete=models.SET_NULL,
                related_name='order',
                to='store.cart',
            ),
        ),
    ]
