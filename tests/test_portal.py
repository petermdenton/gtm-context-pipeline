from copy import deepcopy
import hashlib
import http.client
import json
from pathlib import Path
import tempfile
import threading
import time
import unittest

from gtm_pipeline.cli import load, write_run
from gtm_pipeline.portal import initialize, PortalServer, Workspace
from gtm_pipeline.selection import select

ROOT = Path(__file__).resolve().parents[1]


class PortalTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory()
        cls.path = Path(cls.temp.name) / 'first'
        cls.other = Path(cls.temp.name) / 'second'
        cls.password = 'synthetic-test-password'
        for path, example in ((cls.path, 'warehouse-software'), (cls.other, 'model-evaluation')):
            initialize(path, ROOT / 'examples' / example / 'profile.json',
                       'client@example.test', cls.password, synthetic=True)
        cls.server = PortalServer(cls.path, 0)
        cls.thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.thread.start()

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()
        cls.thread.join()
        cls.temp.cleanup()

    def setUp(self):
        with self.server.workspace.connect() as db:
            db.execute('DELETE FROM attempts')
            db.execute('DELETE FROM sessions')

    def request(self, method, path, body=None, token=None, origin=True, host=None):
        conn = http.client.HTTPConnection('127.0.0.1', self.server.server_port)
        headers = {}
        if body is not None:
            headers['Content-Type'] = 'application/json'
        if origin:
            headers['Origin'] = self.server.origin
        if host:
            headers['Host'] = host
        if token:
            headers['Cookie'] = 'portal_session=' + token
        conn.request(method, path, json.dumps(body) if body is not None else None, headers)
        response = conn.getresponse()
        raw = response.read()
        status, response_headers = response.status, dict(response.getheaders())
        conn.close()
        return status, response_headers, raw

    def login(self):
        status, headers, raw = self.request('POST', '/api/login',
                                           {'email': 'client@example.test', 'password': self.password})
        self.assertEqual(status, 200, raw)
        cookie = headers['Set-Cookie']
        self.assertIn('HttpOnly', cookie)
        self.assertIn('SameSite=Strict', cookie)
        return cookie.split(';')[0].split('=', 1)[1]

    def test_authentication_logout_and_private_routes(self):
        self.assertEqual(self.request('GET', '/api/dashboard')[0], 401)
        token = self.login()
        status, headers, raw = self.request('GET', '/api/dashboard', token=token)
        self.assertEqual(status, 200)
        self.assertEqual(headers['Cache-Control'], 'no-store')
        self.assertNotIn('password_hash', raw.decode())
        self.assertNotIn(str(self.path), raw.decode())
        self.assertEqual(self.request('POST', '/api/logout', {}, token=token)[0], 200)
        self.assertEqual(self.request('GET', '/api/dashboard', token=token)[0], 401)

    def test_client_cannot_select_another_workspace(self):
        token = self.login()
        self.assertFalse(Workspace(self.other).authenticated(token))
        self.assertEqual(self.request('GET', '/api/dashboard?client=model-evaluation', token=token)[0], 404)
        for path in ('/portal.json', '/profile.json', '/sessions.sqlite3', '/../private/portal.json', '/api/clients'):
            self.assertEqual(self.request('GET', path, token=token)[0], 404)

    def test_origin_and_host_boundaries(self):
        body = {'email': 'client@example.test', 'password': self.password}
        self.assertEqual(self.request('POST', '/api/login', body, origin=False)[0], 403)
        self.assertEqual(self.request('GET', '/api/dashboard', host='attacker.example')[0], 403)

    def test_expired_sessions_and_hashed_storage(self):
        token = self.login()
        with self.server.workspace.connect() as db:
            stored = db.execute('SELECT token FROM sessions').fetchone()[0]
            self.assertNotEqual(stored, token)
            db.execute('UPDATE sessions SET expires = ?', (time.time() - 1,))
        self.assertEqual(self.request('GET', '/api/dashboard', token=token)[0], 401)

    def test_failed_login_and_rate_limit(self):
        bad = {'email': 'unknown@example.test', 'password': 'invalid'}
        self.assertEqual(self.request('POST', '/api/login', bad)[0], 401)
        with self.server.workspace.connect() as db:
            db.executemany('INSERT INTO attempts(at) VALUES (?)', [(time.time(),)] * 10)
        self.assertEqual(self.request('POST', '/api/login', bad)[0], 429)

    def test_run_integrity_and_cross_client_rejection(self):
        with tempfile.TemporaryDirectory() as temp:
            workspace = initialize(Path(temp) / 'client', ROOT / 'examples/warehouse-software/profile.json',
                                   'client@example.test', self.password, synthetic=True)
            for example in ('warehouse-software', 'model-evaluation'):
                values, refs = {}, {}
                for field in ('profile', 'candidates', 'exclusions'):
                    values[field], refs[field] = load(ROOT / 'examples' / example / f'{field}.json')
                folder = write_run(select(values['profile'], values['candidates'], values['exclusions'], 2,
                                          '2026-10-09'), refs, workspace / 'runs')
                if example == 'warehouse-software':
                    good_folder = folder
            client = Workspace(workspace)
            dashboard = client.dashboard()
            self.assertEqual(len(dashboard['runs']), 1)
            self.assertEqual(dashboard['unavailable_runs'], 1)
            self.assertEqual(dashboard['runs'][0]['result']['profile_id'], 'warehouse-software')
            self.assertNotIn('path', dashboard['runs'][0]['manifest']['input_hashes']['profile'])
            (good_folder / 'next-companies.json').write_text('{}')
            self.assertEqual(client.dashboard()['runs'], [])
            external = Path(temp) / 'external'
            external.mkdir()
            (external / 'manifest.json').write_text('{}')
            (workspace / 'runs' / 'escape').symlink_to(external, target_is_directory=True)
            self.assertEqual(client.dashboard()['unavailable_runs'], 3)

    def test_mismatched_measurement_and_goals_are_rejected(self):
        for filename, value in [('measurement.json', {'profile_id': 'other', 'profile_sha256': 'wrong'}),
                                ('goals.json', {'schema_version': 1, 'profile_id': 'other', 'goals': []}),
                                ('projects.json', {'schema_version': 1, 'profile_id': 'other', 'projects': []}),
                                ('cluster-briefs.json', {'schema_version': 1, 'profile_id': 'other', 'briefs': []})]:
            with self.subTest(filename=filename):
                target = self.path / filename
                target.write_text(json.dumps(value))
                try:
                    with self.assertRaises(ValueError):
                        self.server.workspace.dashboard()
                finally:
                    target.unlink()

    def test_title_collections_are_workspace_scoped_and_validate_titles(self):
        workspace = self.server.workspace
        for filename, key, method in [('projects.json', 'projects', 'projects'),
                                      ('cluster-briefs.json', 'briefs', 'cluster_briefs')]:
            with self.subTest(filename=filename):
                path = self.path / filename
                source = {'schema_version': 1, 'profile_id': workspace.profile['id'],
                          key: [{'title': 'Synthetic collection'}]}
                self.assertEqual(workspace.workspace_titles(filename, key), [])
                try:
                    path.write_text(json.dumps(source))
                    self.assertEqual(workspace.workspace_titles(filename, key), source[key])
                    self.assertEqual(getattr(Workspace(self.other), method)(), [])
                    source[key][0]['title'] = None
                    path.write_text(json.dumps(source))
                    with self.assertRaises(ValueError):
                        getattr(workspace, method)()
                    path.unlink()
                    path.symlink_to(self.other / 'profile.json')
                    with self.assertRaises(ValueError):
                        getattr(workspace, method)()
                finally:
                    path.unlink(missing_ok=True)

    def test_ad_account_links_are_scoped_safe_and_omit_private_fields(self):
        workspace = Workspace(self.path)
        account = {'provider': 'Synthetic Ads', 'account_id': 'synthetic-account',
                   'url': 'https://ads.example.test/account', 'secret': 'must-not-leak'}
        workspace.config['ad_accounts'] = [account]
        self.assertEqual(workspace.dashboard()['ad_accounts'],
                         [{key: account[key] for key in ('provider', 'account_id', 'url')}])
        self.assertEqual(Workspace(self.other).ad_accounts(), [])
        for url in ('javascript:alert(1)', 'http://ads.example.test/',
                    'https://user:secret@ads.example.test/', 'https:///missing-host'):
            account['url'] = url
            with self.subTest(url=url), self.assertRaises(ValueError):
                workspace.ad_accounts()

    def test_provisioning_does_not_overwrite_existing_workspace(self):
        with self.assertRaises(FileExistsError):
            initialize(self.path, ROOT / 'examples/model-evaluation/profile.json', 'client@example.test', self.password)


if __name__ == '__main__':
    unittest.main()
