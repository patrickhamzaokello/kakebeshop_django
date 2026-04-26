# Generated for chat notifications

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('notifications', '0003_add_listing_submitted_type'),
    ]

    operations = [
        migrations.AlterField(
            model_name='notification',
            name='notification_type',
            field=models.CharField(
                choices=[
                    ('ORDER_CREATED', 'Order Created'),
                    ('ORDER_CONTACTED', 'Order Contacted'),
                    ('ORDER_CONFIRMED', 'Order Confirmed'),
                    ('ORDER_COMPLETED', 'Order Completed'),
                    ('ORDER_CANCELLED', 'Order Cancelled'),
                    ('MERCHANT_NEW_ORDER', 'New Order Received'),
                    ('MERCHANT_APPROVED', 'Merchant Account Approved'),
                    ('MERCHANT_REACTIVATED', 'Merchant Account Reactivated'),
                    ('MERCHANT_SUSPENDED', 'Merchant Account Suspended'),
                    ('MERCHANT_BANNED', 'Merchant Account Banned'),
                    ('LISTING_SUBMITTED', 'Listing Submitted for Review'),
                    ('LISTING_APPROVED', 'Listing Approved'),
                    ('LISTING_REJECTED', 'Listing Rejected'),
                    ('CHAT_MESSAGE', 'Chat Message'),
                ],
                max_length=50,
            ),
        ),
    ]
