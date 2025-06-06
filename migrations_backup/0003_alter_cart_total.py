from django.db import migrations, models

class Migration(migrations.Migration):

    dependencies = [
        ('store', '0002_add_total_to_cart'),
    ]

    operations = [
        migrations.AlterField(
            model_name='cart',
            name='total',
            field=models.DecimalField(decimal_places=2, default=0, max_digits=10, null=True, blank=True),
        ),
    ]
