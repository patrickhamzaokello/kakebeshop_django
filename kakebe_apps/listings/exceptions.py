# kakebe_apps/listings/exceptions.py

from rest_framework.exceptions import APIException
from rest_framework import status


class ListingNotOwnedException(APIException):
    """Raised when a user tries to modify a listing they don't own"""
    status_code = status.HTTP_403_FORBIDDEN
    default_detail = 'You do not own this listing.'
    default_code = 'not_owned'


class MerchantProfileRequiredException(APIException):
    """Raised when a user without merchant profile tries to access merchant-only features"""
    status_code = status.HTTP_403_FORBIDDEN
    default_detail = 'You must have a merchant profile to perform this action.'
    default_code = 'merchant_profile_required'


class ListingNotActiveException(APIException):
    """Raised when trying to perform an action on an inactive listing"""
    status_code = status.HTTP_400_BAD_REQUEST
    default_detail = 'This listing is not active.'
    default_code = 'listing_not_active'


class ListingNotVerifiedException(APIException):
    """Raised when trying to perform an action requiring verification"""
    status_code = status.HTTP_400_BAD_REQUEST
    default_detail = 'This listing is not verified.'
    default_code = 'listing_not_verified'


class ImageGroupNotFoundException(APIException):
    """Raised when specified image groups are not found"""
    status_code = status.HTTP_404_NOT_FOUND
    default_detail = 'One or more image groups not found.'
    default_code = 'image_group_not_found'


class ImageGroupAlreadyAttachedException(APIException):
    """Raised when trying to attach an already attached image group"""
    status_code = status.HTTP_400_BAD_REQUEST
    default_detail = 'Image group is already attached to a listing.'
    default_code = 'image_group_already_attached'


class InvalidStatusTransitionException(APIException):
    """Raised when an invalid status transition is attempted"""
    status_code = status.HTTP_400_BAD_REQUEST
    default_detail = 'Invalid status transition.'
    default_code = 'invalid_status_transition'


class ListingExpiredException(APIException):
    """Raised when a listing has expired"""
    status_code = status.HTTP_400_BAD_REQUEST
    default_detail = 'This listing has expired.'
    default_code = 'listing_expired'


class MaxListingsReachedException(APIException):
    """Raised when merchant has reached their listing limit"""
    status_code = status.HTTP_400_BAD_REQUEST
    default_detail = 'You have reached the maximum number of listings allowed.'
    default_code = 'max_listings_reached'


class InvalidPriceConfigurationException(APIException):
    """Raised when price configuration is invalid"""
    status_code = status.HTTP_400_BAD_REQUEST
    default_detail = 'Invalid price configuration.'
    default_code = 'invalid_price_configuration'


class DuplicateBusinessHourException(APIException):
    """Raised when trying to add duplicate business hours for a day"""
    status_code = status.HTTP_400_BAD_REQUEST
    default_detail = 'Business hours for this day already exist.'
    default_code = 'duplicate_business_hour'