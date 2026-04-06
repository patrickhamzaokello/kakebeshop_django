import logging
import traceback

from django.http import JsonResponse
from rest_framework import status
from rest_framework.exceptions import APIException
from rest_framework.views import exception_handler

logger = logging.getLogger('kakebe_shop_logs')


def custom_exception_handler(exc, context):
    """
    Custom DRF exception handler that always returns JSON.
    Replaces Django's HTML debug/error pages for API requests.
    """
    response = exception_handler(exc, context)

    if response is not None:
        # DRF handled it — normalise the shape
        error_detail = response.data

        # Flatten single-key 'detail' responses
        if isinstance(error_detail, dict) and list(error_detail.keys()) == ['detail']:
            error_detail = str(error_detail['detail'])

        response.data = {
            'success': False,
            'status_code': response.status_code,
            'error': error_detail,
        }
        return response

    # Unhandled exception — log the full traceback and return 500 JSON
    logger.error(
        'Unhandled exception: %s\n%s',
        exc,
        traceback.format_exc(),
        exc_info=True,
        extra={
            'view': context.get('view'),
            'request': context.get('request'),
        },
    )

    return None  # Let Django's handler500 / middleware handle it


# ── Django-level JSON error views (registered in urls.py) ────────────────────

def json_400(request, exception=None):
    logger.warning('400 Bad Request: %s', request.path)
    return JsonResponse(
        {'success': False, 'status_code': 400, 'error': 'Bad request.'},
        status=400,
    )


def json_403(request, exception=None):
    logger.warning('403 Forbidden: %s', request.path)
    return JsonResponse(
        {'success': False, 'status_code': 403, 'error': 'Forbidden.'},
        status=403,
    )


def json_404(request, exception=None):
    logger.warning('404 Not Found: %s', request.path)
    return JsonResponse(
        {'success': False, 'status_code': 404, 'error': 'Not found.'},
        status=404,
    )


def json_500(request):
    logger.error('500 Internal Server Error: %s', request.path)
    return JsonResponse(
        {'success': False, 'status_code': 500, 'error': 'Internal server error.'},
        status=500,
    )
