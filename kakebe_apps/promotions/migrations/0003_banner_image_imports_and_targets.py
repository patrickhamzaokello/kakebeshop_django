import uuid

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('imagehandler', '0002_banner_image_type'),
        ('merchants', '0005_fix_empty_business_email'),
        ('promotions', '0002_remove_campaignplacement_creative_and_more'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.AlterField(
            model_name='promotionalbanner',
            name='image',
            field=models.URLField(blank=True, help_text='Main banner image URL'),
        ),
        migrations.AlterField(
            model_name='promotionalbanner',
            name='link_type',
            field=models.CharField(
                choices=[
                    ('LISTING', 'Single Listing'),
                    ('LISTINGS', 'Multiple Listings'),
                    ('CATEGORY', 'Category'),
                    ('MERCHANT', 'Merchant'),
                    ('URL', 'External URL'),
                    ('NONE', 'No Link'),
                ],
                default='NONE',
                max_length=20,
            ),
        ),
        migrations.AddField(
            model_name='promotionalbanner',
            name='image_asset',
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name='primary_promotional_banners',
                to='imagehandler.imageasset',
            ),
        ),
        migrations.AddField(
            model_name='promotionalbanner',
            name='mobile_image_asset',
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name='mobile_promotional_banners',
                to='imagehandler.imageasset',
            ),
        ),
        migrations.AddField(
            model_name='promotionalbanner',
            name='link_merchant',
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name='promotional_banners',
                to='merchants.merchant',
            ),
        ),
        migrations.CreateModel(
            name='BannerAgentCredential',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('name', models.CharField(max_length=120, unique=True)),
                ('token_prefix', models.CharField(blank=True, db_index=True, max_length=12)),
                ('token_hash', models.CharField(blank=True, max_length=128)),
                ('is_active', models.BooleanField(db_index=True, default=True)),
                ('last_used_at', models.DateTimeField(blank=True, null=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
            ],
            options={
                'db_table': 'banner_agent_credentials',
                'ordering': ['name'],
            },
        ),
        migrations.CreateModel(
            name='BannerImageImport',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('source_path', models.CharField(max_length=500, unique=True)),
                ('sidecar_path', models.CharField(blank=True, max_length=500)),
                (
                    'target_field',
                    models.CharField(
                        choices=[('image', 'Primary Image'), ('mobile_image', 'Mobile Image')],
                        default='image',
                        max_length=20,
                    ),
                ),
                (
                    'status',
                    models.CharField(
                        choices=[
                            ('PENDING', 'Pending'),
                            ('PROCESSING', 'Processing'),
                            ('UPLOADED', 'Uploaded'),
                            ('FAILED', 'Failed'),
                        ],
                        db_index=True,
                        default='PENDING',
                        max_length=20,
                    ),
                ),
                ('error_message', models.TextField(blank=True)),
                ('metadata', models.JSONField(blank=True, default=dict)),
                ('processed_at', models.DateTimeField(blank=True, null=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                (
                    'banner',
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name='image_imports',
                        to='promotions.promotionalbanner',
                    ),
                ),
                (
                    'uploaded_by_agent',
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name='banner_imports',
                        to='promotions.banneragentcredential',
                    ),
                ),
                (
                    'image_asset',
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name='banner_imports',
                        to='imagehandler.imageasset',
                    ),
                ),
            ],
            options={
                'db_table': 'banner_image_imports',
                'ordering': ['created_at'],
            },
        ),
        migrations.AddIndex(
            model_name='bannerimageimport',
            index=models.Index(fields=['status', 'created_at'], name='banner_imag_status_2f1215_idx'),
        ),
        migrations.AddIndex(
            model_name='bannerimageimport',
            index=models.Index(fields=['banner', 'target_field'], name='banner_imag_banner__7ea7c1_idx'),
        ),
    ]
