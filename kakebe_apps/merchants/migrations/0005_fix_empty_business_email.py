from django.db import migrations


def normalize_empty_business_emails(apps, schema_editor):
    """Convert any empty-string business_email values to NULL.

    Empty strings violate the unique constraint in PostgreSQL because they are
    treated as a real value (unlike NULL). Any merchant that was saved without
    a business email must store NULL, not ''.
    """
    Merchant = apps.get_model("merchants", "Merchant")
    Merchant.objects.filter(business_email="").update(business_email=None)


class Migration(migrations.Migration):

    dependencies = [
        ("merchants", "0004_merchant_location"),
    ]

    operations = [
        migrations.RunPython(
            normalize_empty_business_emails,
            reverse_code=migrations.RunPython.noop,
        ),
    ]
