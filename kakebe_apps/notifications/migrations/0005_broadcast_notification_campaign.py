# Generated for admin scheduled broadcasts

import django.db.models.deletion
import uuid
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('notifications', '0004_add_chat_message_type'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
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
                    ('ADMIN_BROADCAST', 'Admin Broadcast'),
                ],
                max_length=50,
            ),
        ),
        migrations.CreateModel(
            name='BroadcastNotificationCampaign',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('channel', models.CharField(choices=[('EMAIL', 'Email'), ('PUSH', 'Push Notification')], db_index=True, max_length=20)),
                ('title', models.CharField(max_length=255)),
                ('message', models.TextField()),
                ('metadata', models.JSONField(blank=True, default=dict)),
                ('scheduled_at', models.DateTimeField(db_index=True)),
                ('status', models.CharField(choices=[('SCHEDULED', 'Scheduled'), ('SENDING', 'Sending'), ('SENT', 'Sent'), ('FAILED', 'Failed'), ('CANCELLED', 'Cancelled')], db_index=True, default='SCHEDULED', max_length=20)),
                ('celery_task_id', models.CharField(blank=True, max_length=255)),
                ('target_count', models.PositiveIntegerField(default=0)),
                ('notification_count', models.PositiveIntegerField(default=0)),
                ('error_message', models.TextField(blank=True)),
                ('sent_at', models.DateTimeField(blank=True, null=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('created_by', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='created_broadcast_campaigns', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'db_table': 'broadcast_notification_campaigns',
                'ordering': ['-scheduled_at', '-created_at'],
                'indexes': [
                    models.Index(fields=['status', 'scheduled_at'], name='broadcast_n_status_9d12d0_idx'),
                    models.Index(fields=['channel', 'status'], name='broadcast_n_channel_c48b9c_idx'),
                    models.Index(fields=['created_by'], name='broadcast_n_created_4f596c_idx'),
                ],
            },
        ),
    ]
