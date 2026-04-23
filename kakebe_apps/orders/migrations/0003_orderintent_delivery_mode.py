from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('orders', '0002_ordergroup_orderintent_order_group_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='orderintent',
            name='delivery_mode',
            field=models.CharField(
                blank=True,
                choices=[
                    ('PICKUP', 'Pickup'),
                    ('DELIVERY', 'Delivery'),
                    ('DIGITAL', 'Digital'),
                    ('IN_PERSON', 'In Person'),
                    ('REMOTE', 'Remote'),
                ],
                max_length=20,
                null=True,
            ),
        ),
    ]
