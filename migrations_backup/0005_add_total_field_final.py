from django.db import migrations, models

class Migration(migrations.Migration):

    dependencies = [
        ('store', '0004_add_total_field'),
    ]

    operations = [
        migrations.AddField(
            model_name='cart',
            name='total',
            field=models.DecimalField(decimal_places=2, default=0, max_digits=10, null=True, blank=True),
            preserve_default=True,
        ),
        migrations.RunSQL(
            """
            -- Set default value for existing rows
            UPDATE store_cart SET total = 0 WHERE total IS NULL;
            -- Modify the column to be NOT NULL with default 0
            ALTER TABLE store_cart MODIFY COLUMN total DECIMAL(10,2) NOT NULL DEFAULT 0;
            """,
            reverse_sql="""
            ALTER TABLE store_cart MODIFY COLUMN total DECIMAL(10,2) NULL;
            """
        ),
    ]
