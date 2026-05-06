from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('listings', '0006_home_feed_quality_fields'),
    ]

    operations = [
        migrations.AddField(
            model_name='listing',
            name='available_from',
            field=models.DateTimeField(blank=True, db_index=True, null=True),
        ),
        migrations.AddField(
            model_name='listing',
            name='available_until',
            field=models.DateTimeField(blank=True, db_index=True, null=True),
        ),
        migrations.AddIndex(
            model_name='listing',
            index=models.Index(
                fields=['available_from', 'available_until'],
                name='listings_avail_8b18f4_idx',
            ),
        ),
    ]
