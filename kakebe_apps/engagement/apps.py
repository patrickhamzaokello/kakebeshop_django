from django.apps import AppConfig


class EngagementConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'kakebe_apps.engagement'

    def ready(self):
        import kakebe_apps.engagement.signals
