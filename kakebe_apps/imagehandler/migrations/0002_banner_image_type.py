from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('imagehandler', '0001_initial'),
    ]

    operations = [
        migrations.AlterField(
            model_name='imageasset',
            name='image_type',
            field=models.CharField(
                choices=[
                    ('listing', 'Listing'),
                    ('banner', 'Promotional Banner'),
                    ('profile', 'Profile'),
                    ('store_banner', 'Store Banner'),
                    ('store_cover', 'Store Cover'),
                ],
                max_length=20,
            ),
        ),
        migrations.AlterField(
            model_name='imageasset',
            name='variant',
            field=models.CharField(
                choices=[
                    ('thumb', 'Thumbnail'),
                    ('medium', 'Medium'),
                    ('large', 'Large'),
                    ('mobile', 'Mobile'),
                ],
                max_length=20,
            ),
        ),
    ]
