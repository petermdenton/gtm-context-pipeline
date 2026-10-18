"""Offline access control and OIDC callback boundary tests with synthetic identities."""

import hashlib
import http.client
import json
from pathlib import Path
import tempfile
import threading
import time
import unittest
from unittest.mock import Mock
from urllib.parse import parse_qs, urlencode, urlsplit

from gtm_pipeline.portal import initialize, PortalServer, Workspace
from gtm_pipeline.portal_access import normalize_domain
from gtm_pipeline.adapters.google_identity import GoogleIdentity, validate_claims

ROOT = Path(__file__).resolve().parents[1]
ADMIN = {'email': 'owner@gmail.com', 'subject': 'synthetic-owner', 'domain': None}
CLIENT = {'email': 'person@client.example', 'subject': 'synthetic-client', 'domain': 'client.example'}


class AccessTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        path = initialize(Path(self.temp.name) / 'client', ROOT / 'examples/warehouse-software/profile.json',
                          'operator@example.test', 'synthetic-password', synthetic=True)
        self.workspace = Workspace(path)
        self.access = self.workspace.access
        self.access.admin_emails = frozenset([ADMIN['email']])
        self.operator = self.access.principal(self.access.local_session())

    def tearDown(self):
        self.temp.cleanup()

    def test_organization_access_and_immediate_revocation(self):
        with self.assertRaises(ValueError):
            self.access.google_session(CLIENT)
        self.access.change_domain(self.operator, 'add', 'CLIENT.EXAMPLE')
        token = self.access.google_session(CLIENT)
        self.assertEqual(self.access.principal(token)['role'], 'client')
        for domain in ('sub.client.example', 'other.example', None):
            with self.assertRaises(ValueError):
                self.access.google_session({**CLIENT, 'domain': domain})
        self.access.change_domain(self.operator, 'remove', 'client.example')
        self.assertIsNone(self.access.principal(token))
        self.access.change_domain(self.operator, 'add', 'client.example')
        self.assertIsNone(self.access.principal(token))

    def test_no_client_or_anonymous_domain_mutation(self):
        for actor in (None, {**CLIENT, 'role': 'client'}):
            with self.assertRaises(PermissionError):
                self.access.change_domain(actor, 'add', 'client.example')
        self.assertEqual(self.access.summary()['domains'], [])

    def test_exact_admin_email_is_pinned_to_google_subject(self):
        token = self.access.google_session(ADMIN)
        self.assertEqual(self.access.principal(token)['role'], 'admin')
        with self.assertRaises(ValueError):
            self.access.google_session({**ADMIN, 'subject': 'replacement-identity'})
        with self.assertRaises(ValueError):
            self.access.google_session({**ADMIN, 'email': 'another@gmail.com'})
        self.access.admin_emails = frozenset()
        self.assertIsNone(self.access.principal(token))

    def test_provisioning_is_persistent_idempotent_and_audited(self):
        self.access.change_domain(self.operator, 'add', 'client.example')
        self.access.change_domain(self.operator, 'add', 'client.example')
        reloaded = Workspace(self.workspace.path).access.summary()
        self.assertEqual(len(reloaded['domains']), 1)
        self.assertEqual(len(reloaded['events']), 1)
        self.assertEqual(reloaded['events'][0]['actor'], self.operator['email'])

    def test_domains_reject_urls_wildcards_paths_and_injection(self):
        for value in ('https://client.example', 'person@client.example', '*.client.example', 'client.example/x',
                      '.client.example', '-client.example', 'client..example', 'client.example.', 'localhost',
                      '127.0.0.1', "client.example';DROP TABLE domains", '', None, ['client.example']):
            with self.subTest(value=value), self.assertRaises(ValueError):
                normalize_domain(value)

    def test_flow_is_browser_bound_expiring_and_single_use(self):
        flow = self.access.begin_flow()
        with self.assertRaises(ValueError):
            self.access.consume_flow(flow['state'], 'wrong-browser')
        result = self.access.consume_flow(flow['state'], flow['browser'])
        self.assertEqual(result, {k: flow[k] for k in ('nonce', 'verifier')})
        with self.assertRaises(ValueError):
            self.access.consume_flow(flow['state'], flow['browser'])
        flow = self.access.begin_flow()
        with self.workspace.connect() as db:
            db.execute('UPDATE auth_flows SET expires = ?', (time.time() - 1,))
        with self.assertRaises(ValueError):
            self.access.consume_flow(flow['state'], flow['browser'])

    def test_workspace_sessions_and_domains_are_isolated(self):
        other_path = initialize(Path(self.temp.name) / 'other', ROOT / 'examples/model-evaluation/profile.json',
                                'other@example.test', 'synthetic-password', synthetic=True)
        other = Workspace(other_path)
        self.access.change_domain(self.operator, 'add', 'client.example')
        token = self.access.google_session(CLIENT)
        self.assertIsNone(other.access.principal(token))
        with self.assertRaises(ValueError):
            other.access.google_session(CLIENT)


class GoogleClaimsTests(unittest.TestCase):
    def setUp(self):
        self.claims = {'iss': 'https://accounts.google.com', 'aud': 'client-id', 'sub': 'synthetic-subject',
                       'nonce': 'synthetic-nonce', 'email': 'person@client.example', 'email_verified': True,
                       'hd': 'client.example'}

    def test_required_google_claims_and_nonce(self):
        identity = validate_claims(self.claims, 'client-id', 'synthetic-nonce')
        self.assertEqual(identity['domain'], 'client.example')
        for field, value in [('aud', 'other-client'), ('iss', 'https://attacker.example'), ('azp', 'other-client'),
                             ('nonce', 'wrong'), ('nonce', None), ('email_verified', False), ('email_verified', 'true'),
                             ('sub', ''), ('email', 'invalid')]:
            with self.subTest(field=field), self.assertRaises(ValueError):
                validate_claims({**self.claims, field: value}, 'client-id', 'synthetic-nonce')

    def test_email_suffix_never_grants_company_membership(self):
        claims = {k: v for k, v in self.claims.items() if k != 'hd'}
        with self.assertRaises(ValueError):
            validate_claims(claims, 'client-id', 'synthetic-nonce')
        identity = validate_claims({**claims, 'email': ADMIN['email']}, 'client-id', 'synthetic-nonce')
        self.assertIsNone(identity['domain'])

    def test_authorization_uses_minimum_scopes_state_nonce_and_pkce(self):
        adapter = GoogleIdentity.__new__(GoogleIdentity)
        adapter.client_id = 'synthetic-client.apps.googleusercontent.com'
        query = parse_qs(urlsplit(adapter.authorization_url('http://127.0.0.1:8765/auth/google/callback',
                         {'state': 's', 'nonce': 'n', 'verifier': 'v'})).query)
        self.assertEqual(query['scope'], ['openid email'])
        self.assertEqual(query['state'], ['s'])
        self.assertEqual(query['nonce'], ['n'])
        self.assertEqual(query['code_challenge_method'], ['S256'])
        self.assertNotIn('client_secret', query)


class CallbackTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        path = initialize(Path(self.temp.name) / 'client', ROOT / 'examples/warehouse-software/profile.json',
                          'operator@example.test', 'synthetic-password', synthetic=True)
        self.server = PortalServer(path, 0, google_admin_emails=[ADMIN['email']])
        self.server.google = Mock()
        self.server.google.authorization_url.return_value = 'https://accounts.google.com/synthetic-test'
        self.server.google.authenticate.return_value = CLIENT
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        self.access = self.server.workspace.access
        self.operator_token = self.access.local_session()
        self.access.change_domain(self.access.principal(self.operator_token), 'add', 'client.example')

    def tearDown(self):
        self.server.shutdown()
        self.server.server_close()
        self.thread.join()
        self.temp.cleanup()

    def request(self, method, path, body=None, cookie='', origin=True):
        conn = http.client.HTTPConnection('127.0.0.1', self.server.server_port)
        headers = {'Cookie': cookie}
        if origin:
            headers['Origin'] = self.server.origin
        if body is not None:
            headers['Content-Type'] = 'application/json'
        conn.request(method, path, None if body is None else json.dumps(body), headers)
        response = conn.getresponse()
        result = response.status, response.getheaders(), response.read()
        conn.close()
        return result

    def test_callback_creates_client_session_and_admin_routes_remain_private(self):
        flow = self.access.begin_flow()
        status, headers, _ = self.request('GET', '/auth/google/callback?' + urlencode({'state': flow['state'], 'code': 'fake-code'}),
                                          cookie='portal_oauth=' + flow['browser'])
        self.assertEqual(status, 303)
        cookies = [v for k, v in headers if k == 'Set-Cookie']
        cookie = next(v.split(';')[0] for v in cookies if v.startswith('portal_session='))
        status, _, raw = self.request('GET', '/api/dashboard', cookie=cookie)
        self.assertEqual(status, 200)
        payload = json.loads(raw)
        self.assertEqual(payload['identity']['role'], 'client')
        self.assertNotIn('access', payload)
        self.assertEqual(payload['client']['email'], CLIENT['email'])
        self.assertEqual(self.request('POST', '/api/admin/domains', {'action': 'add', 'domain': 'other.example'}, cookie)[0], 403)
        # Consumed callbacks cannot sign in twice.
        self.server.google.authenticate.reset_mock()
        _, headers, _ = self.request('GET', '/auth/google/callback?' + urlencode({'state': flow['state'], 'code': 'fake-code'}), cookie='portal_oauth=' + flow['browser'])
        self.assertIn(('Location', '/?auth_error=verification'), headers)
        self.server.google.authenticate.assert_not_called()

    def test_callback_rejects_forgery_duplicates_denied_and_unapproved(self):
        for mode in ('wrong-browser', 'duplicate-state', 'denied', 'unapproved', 'bad-token'):
            with self.subTest(mode=mode):
                flow = self.access.begin_flow()
                query = urlencode({'state': flow['state'], 'code': 'fake-code'})
                cookie = 'portal_oauth=' + flow['browser']
                self.server.google.authenticate.side_effect = None
                self.server.google.authenticate.return_value = CLIENT
                if mode == 'wrong-browser': cookie = 'portal_oauth=wrong'
                if mode == 'duplicate-state': query += '&state=other'
                if mode == 'denied': query = urlencode({'state': flow['state'], 'error': 'access_denied'})
                if mode == 'unapproved': self.server.google.authenticate.return_value = {**CLIENT, 'domain': 'other.example'}
                if mode == 'bad-token': self.server.google.authenticate.side_effect = ValueError('bad token')
                status, headers, _ = self.request('GET', '/auth/google/callback?' + query, cookie=cookie)
                self.assertEqual(status, 303)
                self.assertFalse(any(k == 'Set-Cookie' and v.startswith('portal_session=') for k,v in headers))
                self.assertTrue(dict(headers)['Location'].startswith('/?auth_error='))

    def test_admin_mutations_require_session_role_and_origin(self):
        body = {'action': 'add', 'domain': 'new.example'}
        cookie = 'portal_session=' + self.operator_token
        self.assertEqual(self.request('POST', '/api/admin/domains', body)[0], 401)
        self.assertEqual(self.request('POST', '/api/admin/domains', body, cookie, origin=False)[0], 403)
        self.assertEqual(self.request('POST', '/api/admin/domains', body, cookie)[0], 200)
        status, _, raw = self.request('GET', '/api/dashboard', cookie=cookie)
        self.assertEqual(status, 200)
        self.assertIn('new.example', raw.decode())
        self.assertNotIn('client_secret', raw.decode())

    def test_start_requires_origin_and_sets_browser_cookie(self):
        self.assertEqual(self.request('POST', '/api/auth/google', {}, origin=False)[0], 403)
        status, headers, _ = self.request('POST', '/api/auth/google', {})
        self.assertEqual(status, 200)
        self.assertIn('SameSite=Lax', dict(headers)['Set-Cookie'])
        self.assertIn('HttpOnly', dict(headers)['Set-Cookie'])
        self.server.google = None
        self.assertEqual(self.request('POST', '/api/auth/google', {})[0], 503)

# The stdlib-only suite works without the provider extra. Installing .[google]
# additionally exercises the real verifier with locally signed synthetic tokens.
try:
    from google.auth import crypt, jwt
    from google.oauth2 import id_token
    from cryptography.hazmat.primitives import serialization
    from cryptography.hazmat.primitives.asymmetric import rsa
    HAS_GOOGLE = True
except ImportError:
    HAS_GOOGLE = False


@unittest.skipUnless(HAS_GOOGLE, 'Install .[google] to run real signature verification tests')
class GoogleSignatureTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
        private = key.private_bytes(serialization.Encoding.PEM, serialization.PrivateFormat.PKCS8, serialization.NoEncryption())
        cls.public = key.public_key().public_bytes(serialization.Encoding.PEM, serialization.PublicFormat.SubjectPublicKeyInfo).decode()
        cls.signer = crypt.RSASigner.from_string(private, key_id='synthetic-key')

    def adapter(self, claims, tamper=False):
        from unittest.mock import MagicMock
        from types import SimpleNamespace
        import base64
        encoded = jwt.encode(self.signer, claims).decode()
        if tamper:
            header, _, signature = encoded.split('.')
            payload = base64.urlsafe_b64encode(json.dumps({**claims, 'email': 'attacker@client.example'}).encode()).rstrip(b'=').decode()
            encoded = '.'.join((header, payload, signature))
        adapter = GoogleIdentity.__new__(GoogleIdentity)
        adapter.client_id, adapter.client_secret = 'synthetic-client-id', 'synthetic-secret'
        adapter._id_token = id_token
        cert_response = SimpleNamespace(status=200, data=json.dumps({'synthetic-key': self.public}).encode())
        adapter._Request = Mock(return_value=Mock(return_value=cert_response))
        session = MagicMock()
        session.post.return_value.status_code = 200
        session.post.return_value.json.return_value = {'id_token': encoded}
        adapter._requests = Mock()
        adapter._requests.Session.return_value.__enter__ = Mock(return_value=session)
        adapter._requests.Session.return_value.__exit__ = Mock(return_value=False)
        return adapter

    def claims(self):
        return {'iss': 'https://accounts.google.com', 'aud': 'synthetic-client-id', 'iat': int(time.time()),
                'exp': int(time.time()) + 3600, 'sub': CLIENT['subject'], 'email': CLIENT['email'],
                'hd': CLIENT['domain'], 'email_verified': True, 'nonce': 'synthetic-nonce'}

    def authenticate(self, adapter):
        return adapter.authenticate('synthetic-code', 'http://127.0.0.1:8765/auth/google/callback',
                                    {'nonce': 'synthetic-nonce', 'verifier': 'synthetic-verifier'})

    def test_real_google_auth_verifier_accepts_valid_signature(self):
        self.assertEqual(self.authenticate(self.adapter(self.claims())), CLIENT)

    def test_real_verifier_rejects_forgery_expiry_issuer_and_audience(self):
        for field, value in [('exp', int(time.time()) - 60), ('iat', int(time.time()) + 3600),
                             ('iss', 'https://attacker.example'), ('aud', 'other-client')]:
            with self.subTest(field=field), self.assertRaises(ValueError):
                self.authenticate(self.adapter({**self.claims(), field: value}))
        with self.assertRaises(ValueError):
            self.authenticate(self.adapter(self.claims(), tamper=True))
