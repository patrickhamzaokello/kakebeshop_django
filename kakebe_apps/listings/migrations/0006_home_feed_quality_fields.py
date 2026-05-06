from decimal import Decimal

import django.core.validators
from django.db import migrations, models


def approve_existing_public_listings(apps, schema_editor):
    Listing = apps.get_model('listings', 'Listing')
    Listing.objects.filter(
        status='ACTIVE',
        is_verified=True,
        deleted_at__isnull=True,
        merchant__verified=True,
    ).update(
        is_home_feed_eligible=True,
        quality_status='APPROVED',
        quality_score=Decimal('50.00'),
    )


def reset_existing_public_listings(apps, schema_editor):
    Listing = apps.get_model('listings', 'Listing')
    Listing.objects.filter(
        quality_status='APPROVED',
        quality_score=Decimal('50.00'),
    ).update(
        is_home_feed_eligible=False,
        quality_status='PENDING',
        quality_score=Decimal('0.00'),
    )


class Migration(migrations.Migration):

    dependencies = [
        ('listings', '0005_listingdeliverymode'),
    ]

    operations = [
        migrations.AddField(
            model_name='listing',
            name='feed_boost_reason',
            field=models.CharField(blank=True, max_length=255, null=True),
        ),
        migrations.AddField(
            model_name='listing',
            name='feed_boost_until',
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='listing',
            name='feed_rank_boost',
            field=models.PositiveIntegerField(
                db_index=True,
                default=0,
                validators=[django.core.validators.MaxValueValidator(100)],
            ),
        ),
        migrations.AddField(
            model_name='listing',
            name='home_feed_pin_position',
            field=models.PositiveIntegerField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='listing',
            name='home_feed_pin_until',
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='listing',
            name='is_home_feed_eligible',
            field=models.BooleanField(db_index=True, default=False),
        ),
        migrations.AddField(
            model_name='listing',
            name='is_home_feed_pinned',
            field=models.BooleanField(db_index=True, default=False),
        ),
        migrations.AddField(
            model_name='listing',
            name='quality_rejection_reason',
            field=models.TextField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='listing',
            name='quality_score',
            field=models.DecimalField(
                decimal_places=2,
                default=0,
                max_digits=5,
                validators=[
                    django.core.validators.MinValueValidator(0),
                    django.core.validators.MaxValueValidator(100),
                ],
            ),
        ),
        migrations.AddField(
            model_name='listing',
            name='quality_status',
            field=models.CharField(
                choices=[
                    ('PENDING', 'Pending Review'),
                    ('APPROVED', 'Approved'),
                    ('REJECTED', 'Rejected'),
                    ('NEEDS_REVIEW', 'Needs Review'),
                ],
                db_index=True,
                default='PENDING',
                max_length=20,
            ),
        ),
        migrations.RunPython(approve_existing_public_listings, reset_existing_public_listings),
        migrations.AddIndex(
            model_name='listing',
            index=models.Index(
                fields=['is_home_feed_eligible', 'quality_status', 'status'],
                name='listings_is_home_6af4d2_idx',
            ),
        ),
        migrations.AddIndex(
            model_name='listing',
            index=models.Index(
                fields=['is_home_feed_pinned', 'home_feed_pin_position'],
                name='listings_is_home_221b7e_idx',
            ),
        ),
        migrations.AddIndex(
            model_name='listing',
            index=models.Index(fields=['feed_rank_boost'], name='listings_feed_ra_8e2c0b_idx'),
        ),
    ]
