from django.db import migrations, models

class Migration(migrations.Migration):

    dependencies = [
        ('store', '0007_remove_item_count_from_cart'),
    ]

    operations = [
        migrations.AddField(
            model_name='cart',
            name='total',
            field=models.DecimalField(decimal_places=2, default=0, max_digits=10, verbose_name='total'),
        ),
    ]
