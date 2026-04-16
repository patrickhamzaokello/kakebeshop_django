"""
Run this once to verify Sentry and PostHog are correctly wired up.

    python verify_monitoring.py

What it does:
  - Reads your .env and boots Django
  - Sends a test event to PostHog and flushes it synchronously
  - Sends a test exception to Sentry and flushes it synchronously
  - Prints the outcome for each

After running, check:
  - PostHog  → app.posthog.com  → Activity feed → look for distinct_id "verify-script"
  - Sentry   → your project     → Issues         → look for "KakebeShop verification"
"""

import os
import sys
import django
from decouple import config

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'KakebeShop.settings')
django.setup()

# ── PostHog ──────────────────────────────────────────────────────────────────

def verify_posthog():
    import posthog
    from django.conf import settings

    api_key = getattr(settings, 'POSTHOG_API_KEY', '')
    enabled = getattr(settings, 'POSTHOG_ENABLED', False)

    if not api_key:
        print('[PostHog] FAIL  — POSTHOG_API_KEY is empty in .env')
        return False

    if not enabled:
        print('[PostHog] SKIP  — POSTHOG_ENABLED=False')
        return False

    errors = []
    def on_error(err, items):
        errors.append(err)

    posthog.api_key = api_key
    posthog.host    = getattr(settings, 'POSTHOG_HOST', 'https://us.i.posthog.com')
    posthog.on_error = on_error

    posthog.capture(
        distinct_id='verify-script',
        event='verification_test',
        properties={
            'source': 'verify_monitoring.py',
            'environment': getattr(settings, 'SENTRY_ENVIRONMENT', 'unknown'),
        },
    )
    posthog.flush()          # force synchronous send before script exits

    if errors:
        print(f'[PostHog] FAIL  — {errors[0]}')
        return False

    print(f'[PostHog] OK    — event sent to {posthog.host}')
    print(f'           ↳  Check PostHog → Activity → distinct_id "verify-script"')
    return True


# ── Sentry ────────────────────────────────────────────────────────────────────

def verify_sentry():
    import sentry_sdk
    from django.conf import settings

    dsn = getattr(settings, 'SENTRY_DSN', '')
    if not dsn:
        print('[Sentry]  FAIL  — SENTRY_DSN is empty in .env')
        return False

    client = sentry_sdk.get_client()
    if not client.is_active():
        print('[Sentry]  FAIL  — SDK is not initialised (check SENTRY_DSN format)')
        return False

    # Capture a real exception so it shows with a stack trace in Sentry
    try:
        raise RuntimeError('KakebeShop verification — safe to ignore')
    except RuntimeError:
        event_id = sentry_sdk.capture_exception()

    sentry_sdk.flush(timeout=5)   # force synchronous send

    if event_id:
        print(f'[Sentry]  OK    — event_id={event_id}')
        print(f'           ↳  Check Sentry → Issues → "KakebeShop verification"')
        return True
    else:
        print('[Sentry]  FAIL  — capture returned no event_id (DSN may be wrong)')
        return False


# ── Main ──────────────────────────────────────────────────────────────────────

if __name__ == '__main__':
    print('=' * 60)
    print('KakebeShop — monitoring verification')
    print('=' * 60)

    ph_ok  = verify_posthog()
    snt_ok = verify_sentry()

    print('=' * 60)
    if ph_ok and snt_ok:
        print('All checks passed. Both services are receiving data.')
    else:
        print('One or more checks failed — see details above.')
        sys.exit(1)
