"""
PostHog event capture helpers.

Each function is fire-and-forget — it never raises, so a PostHog outage
or bad data cannot break a user-facing request.

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
    try:
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
    except Exception as exc:
        logger.warning('PostHog user_registered failed: %s', exc)


def user_logged_in(user, auth_provider: str = 'email') -> None:
    try:
        identify(user.id, {
            'email': user.email,
            'name': user.name,
            'username': user.username,
            'auth_provider': getattr(user, 'auth_provider', auth_provider),
        })
        capture(user.id, 'user_logged_in', {
            'auth_provider': auth_provider,
        })
    except Exception as exc:
        logger.warning('PostHog user_logged_in failed: %s', exc)


def session_resumed(user_id, user=None) -> None:
    try:
        props = {}
        if user:
            props = {
                'email': user.email,
                'name': user.name,
                'username': user.username,
            }
        identify(user_id, props)
    except Exception as exc:
        logger.warning('PostHog session_resumed failed: %s', exc)


def email_verified(user) -> None:
    try:
        identify(user.id, {'email_verified': True})
        capture(user.id, 'email_verified', {
            'email_domain': user.email.split('@')[-1],
        })
    except Exception as exc:
        logger.warning('PostHog email_verified failed: %s', exc)


def user_logged_out(user_id) -> None:
    try:
        capture(user_id, 'user_logged_out')
    except Exception as exc:
        logger.warning('PostHog user_logged_out failed: %s', exc)


def user_logged_in_social(user_id, provider: str, is_new_user: bool = False,
                           email: str = None, name: str = None, username: str = None) -> None:
    try:
        if not user_id:
            return
        if is_new_user:
            identify(user_id, {
                'email': email,
                'name': name,
                'username': username,
                'auth_provider': provider,
            })
            capture(user_id, 'user_registered', {
                'auth_provider': provider,
                'email_domain': email.split('@')[-1] if email else None,
            })
        capture(user_id, 'user_logged_in', {'auth_provider': provider})
    except Exception as exc:
        logger.warning('PostHog user_logged_in_social failed: %s', exc)


# ── Discovery ────────────────────────────────────────────────────────────────

def listing_viewed(user_id, listing, source: str = None) -> None:
    try:
        capture(user_id, 'listing_viewed', {
            'listing_id': str(listing.id),
            'listing_title': listing.title,
            'category_id': str(listing.category_id) if listing.category_id else None,
            'listing_type': listing.listing_type,
            'price': float(listing.price) if listing.price is not None else None,
            'merchant_id': str(listing.merchant_id),
            'source': source,
        })
    except Exception as exc:
        logger.warning('PostHog listing_viewed failed: %s', exc)


def search_performed(user_id, query: str, results_count: int, search_type: str = 'all',
                     filters: dict = None) -> None:
    try:
        capture(user_id, 'search_performed', {
            'query': query,
            'results_count': results_count,
            'search_type': search_type,
            **(filters or {}),
        })
    except Exception as exc:
        logger.warning('PostHog search_performed failed: %s', exc)


def category_browsed(user_id, category_id: str) -> None:
    try:
        capture(user_id, 'category_browsed', {'category_id': category_id})
    except Exception as exc:
        logger.warning('PostHog category_browsed failed: %s', exc)


# ── Onboarding ────────────────────────────────────────────────────────────────

def marketplace_intent_set(user_id, intent: str) -> None:
    try:
        identify(user_id, {'marketplace_intent': intent})
        capture(user_id, 'marketplace_intent_set', {'intent': intent})
    except Exception as exc:
        logger.warning('PostHog marketplace_intent_set failed: %s', exc)


def onboarding_step_completed(user_id, step: str, all_complete: bool = False) -> None:
    try:
        if all_complete:
            identify(user_id, {'onboarding_complete': True})
        capture(user_id, 'onboarding_step_completed', {
            'step': step,
            'all_complete': all_complete,
        })
    except Exception as exc:
        logger.warning('PostHog onboarding_step_completed failed: %s', exc)


# ── Cart ─────────────────────────────────────────────────────────────────────

def cart_item_added(user_id, listing, quantity: int, was_update: bool = False) -> None:
    try:
        capture(user_id, 'cart_item_added', {
            'listing_id': str(listing.id),
            'listing_title': listing.title,
            'price': float(listing.price) if listing.price is not None else None,
            'quantity': quantity,
            'was_update': was_update,
            'merchant_id': str(listing.merchant_id),
        })
    except Exception as exc:
        logger.warning('PostHog cart_item_added failed: %s', exc)


def cart_item_removed(user_id, listing) -> None:
    try:
        capture(user_id, 'cart_item_removed', {
            'listing_id': str(listing.id),
            'listing_title': listing.title,
            'merchant_id': str(listing.merchant_id),
        })
    except Exception as exc:
        logger.warning('PostHog cart_item_removed failed: %s', exc)


def cart_cleared(user_id) -> None:
    try:
        capture(user_id, 'cart_cleared')
    except Exception as exc:
        logger.warning('PostHog cart_cleared failed: %s', exc)


# ── Wishlist ──────────────────────────────────────────────────────────────────

def wishlist_item_added(user_id, listing) -> None:
    try:
        capture(user_id, 'wishlist_item_added', {
            'listing_id': str(listing.id),
            'listing_title': listing.title,
            'price': float(listing.price) if listing.price is not None else None,
            'merchant_id': str(listing.merchant_id),
        })
    except Exception as exc:
        logger.warning('PostHog wishlist_item_added failed: %s', exc)


# ── Merchant ─────────────────────────────────────────────────────────────────

def merchant_profile_created(user_id, merchant) -> None:
    try:
        identify(user_id, {'is_merchant': True})
        capture(user_id, 'merchant_profile_created', {
            'merchant_id': str(merchant.id),
            'business_name': merchant.business_name,
        })
    except Exception as exc:
        logger.warning('PostHog merchant_profile_created failed: %s', exc)


def merchant_verified(merchant) -> None:
    try:
        user_id = merchant.user_id
        identify(user_id, {'is_verified_merchant': True})
        capture(user_id, 'merchant_verified', {
            'merchant_id': str(merchant.id),
            'business_name': merchant.business_name,
        })
    except Exception as exc:
        logger.warning('PostHog merchant_verified failed: %s', exc)


def listing_submitted_for_review(user_id, count: int = 1) -> None:
    try:
        capture(user_id, 'listing_submitted_for_review', {'listing_count': count})
    except Exception as exc:
        logger.warning('PostHog listing_submitted_for_review failed: %s', exc)


def listing_approved(listing) -> None:
    try:
        capture(listing.merchant.user_id, 'listing_approved', {
            'listing_id': str(listing.id),
            'listing_title': listing.title,
            'merchant_id': str(listing.merchant_id),
        })
    except Exception as exc:
        logger.warning('PostHog listing_approved failed: %s', exc)


# ── Listings ─────────────────────────────────────────────────────────────────

def listing_created(user_id, listing) -> None:
    try:
        capture(user_id, 'listing_created', {
            'listing_id': str(listing.id),
            'title': listing.title,
            'category_id': str(listing.category_id) if listing.category_id else None,
            'has_price': listing.price is not None,
            'price': float(listing.price) if listing.price is not None else None,
        })
    except Exception as exc:
        logger.warning('PostHog listing_created failed: %s', exc)


# ── Phone ─────────────────────────────────────────────────────────────────────

def phone_number_added(user_id, phone: str) -> None:
    try:
        identify(user_id, {'has_phone': True, 'phone_verified': False})
        capture(user_id, 'phone_number_added', {'phone_country': phone[:3] if phone else None})
    except Exception as exc:
        logger.warning('PostHog phone_number_added failed: %s', exc)


def phone_number_verified(user_id, phone: str) -> None:
    try:
        identify(user_id, {'phone_verified': True})
        capture(user_id, 'phone_number_verified', {'phone_country': phone[:3] if phone else None})
    except Exception as exc:
        logger.warning('PostHog phone_number_verified failed: %s', exc)


def phone_verification_failed(user_id) -> None:
    try:
        capture(user_id, 'phone_verification_failed')
    except Exception as exc:
        logger.warning('PostHog phone_verification_failed failed: %s', exc)


def phone_number_updated(user_id, phone: str) -> None:
    try:
        identify(user_id, {'has_phone': True, 'phone_verified': False})
        capture(user_id, 'phone_number_updated', {'phone_country': phone[:3] if phone else None})
    except Exception as exc:
        logger.warning('PostHog phone_number_updated failed: %s', exc)


def phone_number_removed(user_id) -> None:
    try:
        identify(user_id, {'has_phone': False, 'phone_verified': False})
        capture(user_id, 'phone_number_removed')
    except Exception as exc:
        logger.warning('PostHog phone_number_removed failed: %s', exc)


def phone_otp_sent(user_id, phone: str) -> None:
    try:
        capture(user_id, 'phone_otp_sent', {'phone_country': phone[:3] if phone else None})
    except Exception as exc:
        logger.warning('PostHog phone_otp_sent failed: %s', exc)


def phone_otp_delivery_failed(user_id, phone: str) -> None:
    try:
        capture(user_id, 'phone_otp_delivery_failed', {'phone_country': phone[:3] if phone else None})
    except Exception as exc:
        logger.warning('PostHog phone_otp_delivery_failed failed: %s', exc)


# ── Orders ────────────────────────────────────────────────────────────────────

def checkout_started(user_id) -> None:
    try:
        capture(user_id, 'checkout_started')
    except Exception as exc:
        logger.warning('PostHog checkout_started failed: %s', exc)


def checkout_failed(user_id, reason: str) -> None:
    try:
        capture(user_id, 'checkout_failed', {'reason': reason})
    except Exception as exc:
        logger.warning('PostHog checkout_failed failed: %s', exc)


def order_placed(user_id, orders: list, total_amount, order_group=None, currency: str = None) -> None:
    if not _enabled() or not user_id:
        return
    try:
        from django.conf import settings as _settings
        _currency = currency or getattr(_settings, 'DEFAULT_CURRENCY', 'UGX')
        merchant_ids = list({str(o.merchant_id) for o in orders})
        listing_ids = [str(item.listing_id) for o in orders for item in o.items.all()]
        capture(user_id, 'order_placed', {
            'order_count': len(orders),
            'order_ids': [str(o.id) for o in orders],
            'order_group_id': str(order_group.id) if order_group else None,
            'total_amount': float(total_amount),
            'currency': _currency,
            'merchant_ids': merchant_ids,
            'listing_ids': listing_ids,
        })
    except Exception as exc:
        logger.warning('PostHog order_placed failed: %s', exc)


def order_status_changed(user_id, order, old_status: str, new_status: str) -> None:
    try:
        capture(user_id, 'order_status_changed', {
            'order_id': str(order.id),
            'order_number': order.order_number,
            'old_status': old_status,
            'new_status': new_status,
            'merchant_id': str(order.merchant_id),
        })
    except Exception as exc:
        logger.warning('PostHog order_status_changed failed: %s', exc)


def order_cancelled(user_id, order, cancelled_by: str, reason: str = None) -> None:
    try:
        capture(user_id, 'order_cancelled', {
            'order_id': str(order.id),
            'order_number': order.order_number,
            'cancelled_by': cancelled_by,
            'reason': reason,
            'merchant_id': str(order.merchant_id),
            'total_amount': float(order.total_amount),
        })
    except Exception as exc:
        logger.warning('PostHog order_cancelled failed: %s', exc)


def order_completed(user_id, order) -> None:
    try:
        capture(user_id, 'order_completed', {
            'order_id': str(order.id),
            'order_number': order.order_number,
            'merchant_id': str(order.merchant_id),
            'total_amount': float(order.total_amount),
            'buyer_id': str(order.buyer_id),
        })
    except Exception as exc:
        logger.warning('PostHog order_completed failed: %s', exc)
