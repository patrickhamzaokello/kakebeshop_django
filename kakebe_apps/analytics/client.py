import logging

import posthog
from django.conf import settings

logger = logging.getLogger(__name__)


def init_posthog():
    """Configure the module-level PostHog client. Called once from AppConfig.ready()."""
    api_key = getattr(settings, 'POSTHOG_API_KEY', '')

    if not api_key or not getattr(settings, 'POSTHOG_ENABLED', True):
        posthog.disabled = True
        logger.info('PostHog disabled (no API key or POSTHOG_ENABLED=False)')
        return

    posthog.api_key = api_key
    posthog.host = getattr(settings, 'POSTHOG_HOST', 'https://us.i.posthog.com')
    posthog.on_error = lambda error, items: logger.warning('PostHog error: %s', error)

    logger.info('PostHog initialised (host=%s)', posthog.host)
