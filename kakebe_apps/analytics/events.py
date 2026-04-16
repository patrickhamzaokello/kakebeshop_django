"""
PostHog event capture helpers.

Each function is fire-and-forget — it never raises, so a PostHog outage
cannot break a user-facing request.

Usage:
    from kakebe_apps.analytics import events
    events.user_registered(user)
    events.listing_created(request.user.id, listing)
"""
import logging

import posthog
from django.conf import settings

logger = logging.getLogger(__name__)


def _enabled() -> bool:
    return bool(
        getattr(settings, 'POSTHOG_ENABLED', True)
        and getattr(settings, 'POSTHOG_API_KEY', '')
    )


def capture(distinct_id, event: str, properties: dict = None) -> None:
    """Low-level capture. Prefer the named helpers below."""
    if not _enabled() or not distinct_id:
        return
    try:
        posthog.capture(
            distinct_id=str(distinct_id),
            event=event,
            properties=properties or {},
        )
    except Exception as exc:
        logger.warning('PostHog capture failed [%s]: %s', event, exc)


def identify(distinct_id, properties: dict) -> None:
    """Set / update user properties in PostHog."""
    if not _enabled() or not distinct_id:
        return
    try:
        posthog.identify(distinct_id=str(distinct_id), properties=properties)
    except Exception as exc:
        logger.warning('PostHog identify failed [%s]: %s', distinct_id, exc)


# ── Auth ─────────────────────────────────────────────────────────────────────

def user_registered(user) -> None:
    identify(user.id, {
        'email': user.email,
        'name': user.name,
        'username': user.username,
        'auth_provider': user.auth_provider,
        'created_at': user.created_at.isoformat(),
    })
    capture(user.id, 'user_registered', {
        'auth_provider': user.auth_provider,
        'email_domain': user.email.split('@')[-1],
    })


def user_logged_in(user, auth_provider: str = 'email') -> None:
    capture(user.id, 'user_logged_in', {
        'auth_provider': auth_provider,
    })


def email_verified(user) -> None:
    identify(user.id, {'email_verified': True})
    capture(user.id, 'email_verified', {
        'email_domain': user.email.split('@')[-1],
    })


def user_logged_out(user_id) -> None:
    capture(user_id, 'user_logged_out')


def user_logged_in_social(user_id, provider: str) -> None:
    """Called after successful social auth (Google / Apple / Facebook / Twitter)."""
    if not user_id:
        return
    capture(user_id, 'user_logged_in', {'auth_provider': provider})


# ── Merchant ──────────────────────────────────────────────────────────────────

def merchant_profile_created(user_id, merchant) -> None:
    identify(user_id, {'is_merchant': True})
    capture(user_id, 'merchant_profile_created', {
        'merchant_id': str(merchant.id),
        'business_name': merchant.business_name,
    })


# ── Listings ─────────────────────────────────────────────────────────────────

def listing_created(user_id, listing) -> None:
    capture(user_id, 'listing_created', {
        'listing_id': str(listing.id),
        'title': listing.title,
        'category_id': str(listing.category_id) if listing.category_id else None,
        'has_price': listing.price is not None,
        'price': float(listing.price) if listing.price is not None else None,
    })


# ── Orders ────────────────────────────────────────────────────────────────────

def order_placed(user_id, orders: list, total_amount, order_group=None) -> None:
    capture(user_id, 'order_placed', {
        'order_count': len(orders),
        'order_ids': [str(o.id) for o in orders],
        'order_group_id': str(order_group.id) if order_group else None,
        'total_amount': float(total_amount),
    })
