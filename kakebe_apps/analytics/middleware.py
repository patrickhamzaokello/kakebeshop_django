class PostHogIdentifyMiddleware:
    """
    Attaches `request.analytics_distinct_id` to every request.

    For authenticated users this is their UUID (used by event helpers).
    For anonymous requests it is None — events are simply skipped.

    We do NOT call posthog.identify() on every request (expensive).
    Identification happens explicitly at login / registration.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if hasattr(request, 'user') and request.user.is_authenticated:
            request.analytics_distinct_id = str(request.user.id)
        else:
            request.analytics_distinct_id = None

        return self.get_response(request)
