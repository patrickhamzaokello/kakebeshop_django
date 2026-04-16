from django.apps import AppConfig


class AnalyticsConfig(AppConfig):
    name = 'kakebe_apps.analytics'

    def ready(self):
        from .client import init_posthog
        init_posthog()
