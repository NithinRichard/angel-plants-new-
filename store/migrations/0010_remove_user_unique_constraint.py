# Generated by Django 5.0.3 on 2025-05-30 10:51

from django.db import migrations, models
from django.conf import settings

def remove_unique_constraint(apps, schema_editor):
    # This is a no-op since we'll use SQL directly
    pass

class Migration(migrations.Migration):

    dependencies = [
        ('store', '0009_fix_cart_constraints'),
    ]

    operations = [
        migrations.RunSQL(
            sql=""" 
            ALTER TABLE store_cart 
            DROP INDEX user_id,
            ADD INDEX store_cart_user_id (user_id);
            """,
            reverse_sql=""" 
            ALTER TABLE store_cart 
            DROP INDEX store_cart_user_id,
            ADD UNIQUE (user_id);
            """,
        ),
        migrations.AlterField(
            model_name='cart',
            name='user',
            field=models.ForeignKey(
                on_delete=models.CASCADE,
                related_name='carts',
                to=settings.AUTH_USER_MODEL,
                verbose_name='user'
            ),
        ),
    ]
