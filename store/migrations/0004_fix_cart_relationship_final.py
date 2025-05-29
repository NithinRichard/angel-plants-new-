from django.db import migrations, models

class Migration(migrations.Migration):

    dependencies = [
        ('store', '0002_fix_cart_relationship'),
    ]

    operations = [
        # First, drop the foreign key constraint if it exists
        migrations.RunSQL(
            """
            SET @dbname = DATABASE();
            SET @tablename = 'store_order';
            SET @constraint_name = 'store_order_cart_id_3150a667_fk_store_cart_id';
            
            SELECT IF(
                EXISTS(
                    SELECT * FROM information_schema.table_constraints
                    WHERE 
                        constraint_schema = @dbname
                        AND table_name = @tablename
                        AND constraint_name = @constraint_name
                        AND constraint_type = 'FOREIGN KEY'
                ),
                CONCAT('ALTER TABLE store_order DROP FOREIGN KEY ', @constraint_name, ';'),
                'SELECT 1;'
            ) INTO @drop_fk_sql;
            
            PREPARE stmt FROM @drop_fk_sql;
            EXECUTE stmt;
            DEALLOCATE PREPARE stmt;
            """,
            # No reverse SQL as we can't reliably recreate the foreign key
            """
            SELECT 1;
            """
        ),
        
        # Then drop the cart_id column if it exists
        migrations.RunSQL(
            """
            SET @dbname = DATABASE();
            SET @tablename = 'store_order';
            SET @columnname = 'cart_id';
            
            SELECT IF(
                EXISTS(
                    SELECT * FROM information_schema.columns 
                    WHERE 
                        table_schema = @dbname
                        AND table_name = @tablename
                        AND column_name = @columnname
                ),
                'ALTER TABLE store_order DROP COLUMN cart_id;',
                'SELECT 1;'
            ) INTO @drop_column_sql;
            
            PREPARE stmt FROM @drop_column_sql;
            EXECUTE stmt;
            DEALLOCATE PREPARE stmt;
            """,
            # No reverse SQL as we can't reliably recreate the column
            """
            SELECT 1;
            """
        ),
        
        # Finally, ensure the cart field is properly set up
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
