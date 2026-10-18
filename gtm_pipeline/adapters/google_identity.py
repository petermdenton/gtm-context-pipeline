"""Google OIDC authorization code flow. Optional google-auth dependency."""

import base64
from functools import partial
import hashlib
import hmac
import json
from pathlib import Path
from urllib.parse import urlencode

from ..portal_access import normalize_domain


class GoogleIdentity:
    def __init__(self, credentials_path):
        try:
            from google.oauth2 import id_token
            from google.auth.transport.requests import Request
            import requests
        except ImportError as error:
            raise ValueError('Install the optional Google dependency: pip install -e ".[google]"') from error
        credentials = json.loads(Path(credentials_path).read_text())
        config = credentials.get('web', {})
        self.client_id = config.get('client_id')
        self.client_secret = config.get('client_secret')
        if not isinstance(self.client_id, str) or not self.client_id.endswith('.apps.googleusercontent.com') or not isinstance(self.client_secret, str) or not self.client_secret:
            raise ValueError('Use the downloaded Google OAuth web application credentials JSON')
        self._id_token, self._Request, self._requests = id_token, Request, requests

    def authorization_url(self, redirect_uri, flow):
        challenge = base64.urlsafe_b64encode(hashlib.sha256(flow['verifier'].encode()).digest()).rstrip(b'=').decode()
        return 'https://accounts.google.com/o/oauth2/v2/auth?' + urlencode({
            'client_id': self.client_id, 'redirect_uri': redirect_uri, 'response_type': 'code',
            'scope': 'openid email', 'state': flow['state'], 'nonce': flow['nonce'],
            'code_challenge': challenge, 'code_challenge_method': 'S256', 'prompt': 'select_account'})

    def authenticate(self, code, redirect_uri, flow):
        # Provider endpoints are fixed, never taken from the browser or credential file.
        try:
            with self._requests.Session() as session:
                response = session.post('https://oauth2.googleapis.com/token', data={
                    'code': code, 'client_id': self.client_id, 'client_secret': self.client_secret,
                    'redirect_uri': redirect_uri, 'grant_type': 'authorization_code',
                    'code_verifier': flow['verifier']}, timeout=10, allow_redirects=False)
                if response.status_code != 200:
                    raise ValueError('Token exchange failed')
                claims = self._id_token.verify_oauth2_token(
                    response.json()['id_token'], partial(self._Request(session=session), timeout=10), self.client_id)
            return validate_claims(claims, self.client_id, flow['nonce'])
        except Exception as error:
            # Tokens, codes and Google response bodies must never reach logs or the UI.
            raise ValueError('Google sign-in could not be verified. Please try again.') from error


def validate_claims(claims, client_id, nonce):
    """Additional checks after google-auth verifies signature, issuer and time."""
    if (claims.get('aud') != client_id or claims.get('iss') not in ('accounts.google.com', 'https://accounts.google.com')
            or claims.get('azp', client_id) != client_id or claims.get('email_verified') is not True):
        raise ValueError('Invalid Google identity')
    supplied_nonce = claims.get('nonce')
    if not isinstance(supplied_nonce, str) or not hmac.compare_digest(supplied_nonce.encode(), nonce.encode()):
        raise ValueError('Invalid sign-in nonce')
    email, subject = claims.get('email'), claims.get('sub')
    if not isinstance(email, str) or email.count('@') != 1 or not isinstance(subject, str) or not subject:
        raise ValueError('Google identity is incomplete')
    email = email.lower()
    domain = normalize_domain(claims['hd']) if claims.get('hd') else None
    # A suffix alone is not proof of membership. Require Google's hosted-domain
    # assertion for company access. Gmail identities can be explicit agency admins.
    if not domain and email.split('@')[1] != 'gmail.com':
        raise ValueError('A managed Google Workspace account is required')
    return {'email': email, 'subject': subject, 'domain': domain}
