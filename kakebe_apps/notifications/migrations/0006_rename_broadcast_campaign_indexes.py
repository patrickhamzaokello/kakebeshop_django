from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('notifications', '0005_broadcast_notification_campaign'),
    ]

    operations = [
        migrations.RenameIndex(
            model_name='broadcastnotificationcampaign',
            new_name='broadcast_n_status_b4319c_idx',
            old_name='broadcast_n_status_9d12d0_idx',
        ),
        migrations.RenameIndex(
            model_name='broadcastnotificationcampaign',
            new_name='broadcast_n_channel_91d18d_idx',
            old_name='broadcast_n_channel_c48b9c_idx',
        ),
        migrations.RenameIndex(
            model_name='broadcastnotificationcampaign',
            new_name='broadcast_n_created_9281aa_idx',
            old_name='broadcast_n_created_4f596c_idx',
        ),
    ]
