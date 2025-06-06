from django.db import migrations, models
import django.utils.timezone

class Migration(migrations.Migration):

    dependencies = [
        ('store', '0011_remove_cart_total_order_address2_order_district'),
    ]

    operations = [
        migrations.AddField(
            model_name='order',
            name='status_changed',
            field=models.DateTimeField(auto_now_add=True, default=django.utils.timezone.now),
            preserve_default=False,
        ),
    ]
