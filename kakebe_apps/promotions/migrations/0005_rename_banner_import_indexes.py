from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('promotions', '0004_banner_agent_schema_patch'),
    ]

    operations = [
        migrations.RenameIndex(
            model_name='bannerimageimport',
            new_name='banner_imag_status_90522e_idx',
            old_name='banner_imag_status_2f1215_idx',
        ),
        migrations.RenameIndex(
            model_name='bannerimageimport',
            new_name='banner_imag_banner__7bce8b_idx',
            old_name='banner_imag_banner__7ea7c1_idx',
        ),
    ]
