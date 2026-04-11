from rest_framework import renderers
import json


class UserRenderer(renderers.JSONRenderer):
    charset = 'utf-8'

    def render(self, data, accepted_media_type=None, renderer_context=None):
        if renderer_context:
            response = renderer_context.get('response')
            if response and response.status_code >= 400:
                # Only wrap if not already wrapped by the view
                if isinstance(data, dict) and ('errors' in data or 'error' in data):
                    return json.dumps(data)
                return json.dumps({'errors': data})
        return json.dumps(data)