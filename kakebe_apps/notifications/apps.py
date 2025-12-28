# kakebe_apps/notifications/apps.py
from django.apps import AppConfig


class NotificationsConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'kakebe_apps.notifications'
    verbose_name = 'Notifications'

    def ready(self):
        """Import signals when app is ready"""
        import kakebe_apps.notifications.signals