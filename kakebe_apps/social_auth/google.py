from google.auth.transport import requests
from google.oauth2 import id_token


class Google:
    """Google class to fetch the user info and return it"""

    @staticmethod
    def validate(auth_token, audiences=None):
        """
        Verifies a Google ID token against one or more allowed audiences.
        Tries each audience in turn; returns the token payload on the first
        match, or an error string if none succeed.
        """
        if not audiences:
            audiences = [None]  # fall back to no-audience check

        for audience in audiences:
            try:
                idinfo = id_token.verify_oauth2_token(
                    auth_token, requests.Request(), audience=audience)

                if idinfo['iss'] not in ['accounts.google.com', 'https://accounts.google.com']:
                    raise ValueError('Invalid issuer.')

                return idinfo

            except ValueError:
                continue

        return "The token is either invalid or has expired"