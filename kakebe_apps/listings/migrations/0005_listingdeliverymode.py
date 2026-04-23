import django.core.validators
import django.db.models.deletion
import uuid
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('listings', '0004_delete_listingimage'),
    ]

    operations = [
        migrations.CreateModel(
            name='ListingDeliveryMode',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('mode', models.CharField(
                    choices=[
                        ('PICKUP', 'Pickup'),
                        ('DELIVERY', 'Delivery'),
                        ('DIGITAL', 'Digital'),
                        ('IN_PERSON', 'In Person'),
                        ('REMOTE', 'Remote'),
                    ],
                    max_length=20,
                )),
                ('notes', models.CharField(blank=True, max_length=255)),
                ('delivery_fee', models.DecimalField(
                    blank=True,
                    decimal_places=2,
                    max_digits=12,
                    null=True,
                    validators=[django.core.validators.MinValueValidator(0)],
                )),
                ('estimated_days', models.PositiveSmallIntegerField(blank=True, null=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('listing', models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='delivery_modes',
                    to='listings.listing',
                )),
            ],
            options={
                'db_table': 'listing_delivery_modes',
                'unique_together': {('listing', 'mode')},
            },
        ),
        migrations.AddIndex(
            model_name='listingdeliverymode',
            index=models.Index(fields=['listing'], name='listing_del_listing_idx'),
        ),
        migrations.AddIndex(
            model_name='listingdeliverymode',
            index=models.Index(fields=['mode'], name='listing_del_mode_idx'),
        ),
    ]
