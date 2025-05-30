from django.db import migrations, models

class Migration(migrations.Migration):

    dependencies = [
        ('store', '0006_remove_cart_total'),
    ]

    operations = [
        migrations.AddField(
            model_name='cart',
            name='total',
            field=models.DecimalField(
                decimal_places=2,
                default=0,
                max_digits=10,
                verbose_name='total'
            ),
        ),
    ]
