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
        props = _normalise_properties(properties or {})
        props.setdefault('user_id', str(distinct_id))
        posthog.capture(
            distinct_id=str(distinct_id),
            event=event,
            properties=props,
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


def _normalise_properties(properties: dict) -> dict:
    """Convert common IDs/values into PostHog-friendly scalar properties."""
    normalised = {}
    for key, value in properties.items():
        if value is None:
            normalised[key] = None
        elif key.endswith('_id') or key.endswith('_ids'):
            if isinstance(value, (list, tuple, set)):
                normalised[key] = [str(v) for v in value]
            else:
                normalised[key] = str(value)
        elif hasattr(value, 'isoformat'):
            normalised[key] = value.isoformat()
        else:
            normalised[key] = value
    return normalised


def _user_identity(user) -> dict:
    props = {
        'email': getattr(user, 'email', None),
        'name': getattr(user, 'name', None),
        'username': getattr(user, 'username', None),
        'auth_provider': getattr(user, 'auth_provider', None),
        'has_phone': bool(getattr(user, 'phone', None)),
        'phone_verified': bool(getattr(user, 'phone_verified', False)),
        'profile_image_set': bool(getattr(user, 'profile_image', None)),
        'is_staff': bool(getattr(user, 'is_staff', False)),
    }
    if hasattr(user, 'merchant_profile'):
        props.update({
            'is_merchant': True,
            **_merchant_props(user.merchant_profile),
        })
    else:
        props['is_merchant'] = False
    return props


def _merchant_props(merchant) -> dict:
    if not merchant:
        return {}
    return {
        'merchant_id': str(merchant.id),
        'merchant_user_id': str(merchant.user_id),
        'merchant_name': merchant.display_name,
        'business_name': merchant.business_name,
        'merchant_status': merchant.status,
        'merchant_verified': merchant.verified,
        'merchant_featured': merchant.featured,
    }


def _listing_props(listing) -> dict:
    if not listing:
        return {}
    props = {
        'listing_id': str(listing.id),
        'listing_title': listing.title,
        'listing_type': listing.listing_type,
        'listing_status': listing.status,
        'category_id': str(listing.category_id) if listing.category_id else None,
        'price_type': listing.price_type,
        'price': float(listing.price) if listing.price is not None else None,
        'currency': listing.currency,
        'merchant_id': str(listing.merchant_id),
    }
    if hasattr(listing, 'merchant') and listing.merchant:
        props.update(_merchant_props(listing.merchant))
    return props


def _order_props(order) -> dict:
    if not order:
        return {}
    return {
        'order_id': str(order.id),
        'order_number': order.order_number,
        'order_status': order.status,
        'buyer_id': str(order.buyer_id),
        'merchant_id': str(order.merchant_id),
        'order_group_id': str(order.order_group_id) if order.order_group_id else None,
        'total_amount': float(order.total_amount),
        'delivery_fee': float(order.delivery_fee) if order.delivery_fee is not None else None,
        'delivery_mode': order.delivery_mode,
    }


# ── Auth ─────────────────────────────────────────────────────────────────────

def user_registered(user) -> None:
    try:
        identify(user.id, {
            **_user_identity(user),
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
        identify(user.id, {**_user_identity(user), 'auth_provider': getattr(user, 'auth_provider', auth_provider)})
        capture(user.id, 'user_logged_in', {
            'auth_provider': auth_provider,
        })
    except Exception as exc:
        logger.warning('PostHog user_logged_in failed: %s', exc)


def session_resumed(user_id, user=None) -> None:
    try:
        props = {}
        if user:
            props = _user_identity(user)
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
        capture(user_id, 'listing_viewed', {**_listing_props(listing), 'source': source})
    except Exception as exc:
        logger.warning('PostHog listing_viewed failed: %s', exc)


def listing_contacted(user_id, listing, source: str = None) -> None:
    try:
        capture(user_id, 'listing_contacted', {**_listing_props(listing), 'source': source})
    except Exception as exc:
        logger.warning('PostHog listing_contacted failed: %s', exc)


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


def profile_viewed(user) -> None:
    try:
        identify(user.id, _user_identity(user))
        capture(user.id, 'profile_viewed', {
            'is_merchant': hasattr(user, 'merchant_profile'),
            'merchant_id': str(user.merchant_profile.id) if hasattr(user, 'merchant_profile') else None,
        })
    except Exception as exc:
        logger.warning('PostHog profile_viewed failed: %s', exc)


def profile_updated(user, updated_fields=None) -> None:
    try:
        identify(user.id, _user_identity(user))
        capture(user.id, 'profile_updated', {
            'updated_fields': updated_fields or [],
            'is_merchant': hasattr(user, 'merchant_profile'),
            'merchant_id': str(user.merchant_profile.id) if hasattr(user, 'merchant_profile') else None,
        })
    except Exception as exc:
        logger.warning('PostHog profile_updated failed: %s', exc)


def profile_image_updated(user) -> None:
    try:
        identify(user.id, _user_identity(user))
        capture(user.id, 'profile_image_updated', {'profile_image_set': bool(user.profile_image)})
    except Exception as exc:
        logger.warning('PostHog profile_image_updated failed: %s', exc)


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
            **_listing_props(listing),
            'quantity': quantity,
            'was_update': was_update,
        })
    except Exception as exc:
        logger.warning('PostHog cart_item_added failed: %s', exc)


def cart_item_removed(user_id, listing) -> None:
    try:
        capture(user_id, 'cart_item_removed', _listing_props(listing))
    except Exception as exc:
        logger.warning('PostHog cart_item_removed failed: %s', exc)


def cart_viewed(user_id, cart) -> None:
    try:
        merchant_ids = list({str(item.listing.merchant_id) for item in cart.items.select_related('listing').all()})
        capture(user_id, 'cart_viewed', {
            'cart_id': str(cart.id),
            'cart_item_count': cart.items.count(),
            'cart_total_items': cart.total_items,
            'cart_total_price': float(cart.total_price),
            'merchant_ids': merchant_ids,
        })
    except Exception as exc:
        logger.warning('PostHog cart_viewed failed: %s', exc)


def cart_item_quantity_updated(user_id, cart_item, old_quantity: int, new_quantity: int) -> None:
    try:
        capture(user_id, 'cart_item_quantity_updated', {
            **_listing_props(cart_item.listing),
            'cart_id': str(cart_item.cart_id),
            'cart_item_id': str(cart_item.id),
            'old_quantity': old_quantity,
            'new_quantity': new_quantity,
            'quantity_delta': new_quantity - old_quantity,
        })
    except Exception as exc:
        logger.warning('PostHog cart_item_quantity_updated failed: %s', exc)


def cart_cleared(user_id, cart=None, item_count: int = None) -> None:
    try:
        capture(user_id, 'cart_cleared', {
            'cart_id': str(cart.id) if cart else None,
            'cart_item_count': item_count,
        })
    except Exception as exc:
        logger.warning('PostHog cart_cleared failed: %s', exc)


# ── Wishlist ──────────────────────────────────────────────────────────────────

def wishlist_item_added(user_id, listing) -> None:
    try:
        capture(user_id, 'wishlist_item_added', _listing_props(listing))
    except Exception as exc:
        logger.warning('PostHog wishlist_item_added failed: %s', exc)


def wishlist_item_removed(user_id, listing) -> None:
    try:
        capture(user_id, 'wishlist_item_removed', _listing_props(listing))
    except Exception as exc:
        logger.warning('PostHog wishlist_item_removed failed: %s', exc)


# ── Merchant ─────────────────────────────────────────────────────────────────

def merchant_profile_created(user_id, merchant) -> None:
    try:
        identify(user_id, {'is_merchant': True, **_merchant_props(merchant)})
        capture(user_id, 'merchant_profile_created', {
            **_merchant_props(merchant),
        })
    except Exception as exc:
        logger.warning('PostHog merchant_profile_created failed: %s', exc)


def merchant_verified(merchant) -> None:
    try:
        user_id = merchant.user_id
        identify(user_id, {'is_verified_merchant': True, **_merchant_props(merchant)})
        capture(user_id, 'merchant_verified', _merchant_props(merchant))
    except Exception as exc:
        logger.warning('PostHog merchant_verified failed: %s', exc)


def merchant_viewed(user_id, merchant, source: str = None) -> None:
    try:
        capture(user_id, 'merchant_viewed', {**_merchant_props(merchant), 'source': source})
    except Exception as exc:
        logger.warning('PostHog merchant_viewed failed: %s', exc)


def merchant_list_viewed(user_id, results_count: int, search: str = None, filters: dict = None) -> None:
    try:
        capture(user_id, 'merchant_list_viewed', {
            'results_count': results_count,
            'search': search,
            **(filters or {}),
        })
    except Exception as exc:
        logger.warning('PostHog merchant_list_viewed failed: %s', exc)


def merchant_listings_viewed(user_id, merchant, results_count: int, filters: dict = None) -> None:
    try:
        capture(user_id, 'merchant_listings_viewed', {
            **_merchant_props(merchant),
            'results_count': results_count,
            **(filters or {}),
        })
    except Exception as exc:
        logger.warning('PostHog merchant_listings_viewed failed: %s', exc)


def merchant_profile_updated(user_id, merchant, updated_fields=None) -> None:
    try:
        identify(user_id, _merchant_props(merchant))
        capture(user_id, 'merchant_profile_updated', {
            **_merchant_props(merchant),
            'updated_fields': updated_fields or [],
        })
    except Exception as exc:
        logger.warning('PostHog merchant_profile_updated failed: %s', exc)


def merchant_image_updated(user_id, merchant, image_type: str) -> None:
    try:
        capture(user_id, 'merchant_image_updated', {
            **_merchant_props(merchant),
            'image_type': image_type,
        })
    except Exception as exc:
        logger.warning('PostHog merchant_image_updated failed: %s', exc)


def listing_submitted_for_review(user_id, count: int = 1, merchant_id: str = None) -> None:
    try:
        capture(user_id, 'listing_submitted_for_review', {
            'listing_count': count,
            'merchant_id': merchant_id,
        })
    except Exception as exc:
        logger.warning('PostHog listing_submitted_for_review failed: %s', exc)


def listing_approved(listing) -> None:
    try:
        capture(listing.merchant.user_id, 'listing_approved', _listing_props(listing))
    except Exception as exc:
        logger.warning('PostHog listing_approved failed: %s', exc)


# ── Listings ─────────────────────────────────────────────────────────────────

def listing_created(user_id, listing) -> None:
    try:
        from kakebe_apps.listings.models import ListingDeliveryMode
        modes = list(listing.delivery_modes.values_list('mode', flat=True))
        defaults = ListingDeliveryMode.DEFAULT_MODES_BY_TYPE.get(listing.listing_type, [])
        capture(user_id, 'listing_created', {
            **_listing_props(listing),
            'has_price': listing.price is not None,
            'delivery_modes': modes,
            'delivery_modes_count': len(modes),
            'used_default_delivery_modes': sorted(modes) == sorted(defaults),
        })
    except Exception as exc:
        logger.warning('PostHog listing_created failed: %s', exc)


def listing_delivery_mode_added(user_id, listing, mode: str) -> None:
    try:
        capture(user_id, 'listing_delivery_mode_added', {
            **_listing_props(listing),
            'mode': mode,
        })
    except Exception as exc:
        logger.warning('PostHog listing_delivery_mode_added failed: %s', exc)


def listing_delivery_mode_removed(user_id, listing, mode: str) -> None:
    try:
        capture(user_id, 'listing_delivery_mode_removed', {
            **_listing_props(listing),
            'mode': mode,
        })
    except Exception as exc:
        logger.warning('PostHog listing_delivery_mode_removed failed: %s', exc)


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
            'buyer_id': str(user_id),
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
            **_order_props(order),
            'old_status': old_status,
            'new_status': new_status,
            'actor_user_id': str(user_id),
        })
    except Exception as exc:
        logger.warning('PostHog order_status_changed failed: %s', exc)


def order_cancelled(user_id, order, cancelled_by: str, reason: str = None) -> None:
    try:
        capture(user_id, 'order_cancelled', {
            **_order_props(order),
            'cancelled_by': cancelled_by,
            'reason': reason,
            'actor_user_id': str(user_id),
        })
    except Exception as exc:
        logger.warning('PostHog order_cancelled failed: %s', exc)


def order_completed(user_id, order) -> None:
    try:
        capture(user_id, 'order_completed', {**_order_props(order), 'actor_user_id': str(user_id)})
    except Exception as exc:
        logger.warning('PostHog order_completed failed: %s', exc)


def orders_viewed(user_id, role: str, count: int, status: str = None, merchant_id: str = None) -> None:
    try:
        capture(user_id, 'orders_viewed', {
            'role': role,
            'orders_count': count,
            'status': status,
            'merchant_id': merchant_id,
        })
    except Exception as exc:
        logger.warning('PostHog orders_viewed failed: %s', exc)


def order_detail_viewed(user_id, order) -> None:
    try:
        capture(user_id, 'order_detail_viewed', _order_props(order))
    except Exception as exc:
        logger.warning('PostHog order_detail_viewed failed: %s', exc)


def conversation_started(user_id, conversation, message=None) -> None:
    try:
        merchant = conversation.listing.merchant if conversation.listing_id else None
        if not merchant and hasattr(conversation.seller, 'merchant_profile'):
            merchant = conversation.seller.merchant_profile
        capture(user_id, 'conversation_started', {
            'conversation_id': str(conversation.id),
            'buyer_id': str(conversation.buyer_id),
            'seller_user_id': str(conversation.seller_id),
            'listing_id': str(conversation.listing_id) if conversation.listing_id else None,
            'order_id': str(conversation.order_intent_id) if conversation.order_intent_id else None,
            'message_id': str(message.id) if message else None,
            **_merchant_props(merchant),
        })
    except Exception as exc:
        logger.warning('PostHog conversation_started failed: %s', exc)


def message_sent(user_id, conversation, message) -> None:
    try:
        merchant = conversation.listing.merchant if conversation.listing_id else None
        if not merchant and hasattr(conversation.seller, 'merchant_profile'):
            merchant = conversation.seller.merchant_profile
        capture(user_id, 'message_sent', {
            'conversation_id': str(conversation.id),
            'message_id': str(message.id),
            'buyer_id': str(conversation.buyer_id),
            'seller_user_id': str(conversation.seller_id),
            'listing_id': str(conversation.listing_id) if conversation.listing_id else None,
            'order_id': str(conversation.order_intent_id) if conversation.order_intent_id else None,
            'has_attachment': bool(message.attachment),
            **_merchant_props(merchant),
        })
    except Exception as exc:
        logger.warning('PostHog message_sent failed: %s', exc)


def messages_marked_read(user_id, conversation, marked_count: int) -> None:
    try:
        capture(user_id, 'messages_marked_read', {
            'conversation_id': str(conversation.id),
            'marked_count': marked_count,
            'buyer_id': str(conversation.buyer_id),
            'seller_user_id': str(conversation.seller_id),
        })
    except Exception as exc:
        logger.warning('PostHog messages_marked_read failed: %s', exc)
