"""Single-workspace, loopback-only client portal with optional Google identity."""

import argparse
from contextlib import contextmanager
from datetime import datetime, timezone
import getpass
import hashlib
import hmac
from http.cookies import SimpleCookie
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
from pathlib import Path
import secrets
import shutil
import sqlite3
import time
from urllib.parse import parse_qs, urlsplit

from .cli import load, write_run
from .selection import select, validate_profile
from .portal_access import Access
from .portal_projects import ProjectStore
from .adapters.exa_search import ExaSearch

ASSETS = Path(__file__).with_name('portal_static')
SESSION_SECONDS = 8 * 60 * 60


def password_hash(password, salt):
    return hashlib.pbkdf2_hmac('sha256', password.encode(), bytes.fromhex(salt), 600_000).hex()


def initialize(workspace, profile_path, email, password, *, synthetic=False):
    """Provision one client. Existing workspaces are never overwritten."""
    if len(password) < 12:
        raise ValueError('Use a password of at least 12 characters')
    if not email or '@' not in email:
        raise ValueError('An email address is required')
    profile, _ = load(profile_path)
    validate_profile(profile)
    workspace = Path(workspace).resolve()
    workspace.mkdir(parents=True, exist_ok=False, mode=0o700)
    shutil.copyfile(profile_path, workspace / 'profile.json')
    (workspace / 'runs').mkdir(mode=0o700)
    salt = secrets.token_hex(16)
    config = {'schema_version': 1, 'client_id': secrets.token_hex(16),
              'synthetic': synthetic, 'email': email.strip().lower(), 'salt': salt,
              'password_hash': password_hash(password, salt)}
    config_path = workspace / 'portal.json'
    config_path.write_text(json.dumps(config, indent=2) + '\n')
    config_path.chmod(0o600)
    return workspace


class Workspace:
    def __init__(self, path):
        self.path = Path(path).resolve()
        self.config = json.loads((self.path / 'portal.json').read_text())
        self.profile, self.profile_ref = load(self.path / 'profile.json')
        validate_profile(self.profile)
        self.db_path = self.path / 'sessions.sqlite3'
        with self.connect() as db:
            db.execute('CREATE TABLE IF NOT EXISTS sessions (token TEXT PRIMARY KEY, expires REAL)')
            db.execute('CREATE TABLE IF NOT EXISTS attempts (id INTEGER PRIMARY KEY, at REAL)')
        self.db_path.chmod(0o600)
        self.access = Access(self)
        self.project_store = ProjectStore(self)

    @contextmanager
    def connect(self):
        db = sqlite3.connect(self.db_path)
        try:
            with db:
                yield db
        finally:
            db.close()

    def login(self, email, password):
        now = time.time()
        with self.connect() as db:
            db.execute('BEGIN IMMEDIATE')
            db.execute('DELETE FROM attempts WHERE at < ?', (now - 300,))
            if db.execute('SELECT count(*) FROM attempts').fetchone()[0] >= 10:
                return None, 429
            db.execute('INSERT INTO attempts(at) VALUES (?)', (now,))
        valid = hmac.compare_digest(password_hash(password, self.config['salt']),
                                    self.config['password_hash'])
        if not valid or not hmac.compare_digest(email.strip().lower().encode(), self.config['email'].encode()):
            return None, 401
        return self.access.local_session(), 200

    def authenticated(self, token):
        return self.access.principal(token) is not None

    def logout(self, token):
        with self.connect() as db:
            db.execute('DELETE FROM sessions WHERE token = ?', (hashlib.sha256(token.encode()).hexdigest(),))

    def goals(self):
        path = self.path / 'goals.json'
        if not path.exists():
            return []
        if not path.resolve().is_relative_to(self.path):
            raise ValueError('Goals leave workspace')
        source = json.loads(path.read_text())
        if source.get('schema_version') != 1 or source.get('profile_id') != self.profile['id']:
            raise ValueError('Goals do not match workspace')
        goals = source['goals']
        if not isinstance(goals, list) or len({g['id'] for g in goals}) != len(goals):
            raise ValueError('Invalid goals')
        for goal in goals:
            if goal['status'] not in ('proposed', 'agreed', 'in_progress', 'paused', 'achieved'):
                raise ValueError('Invalid goal status')
            for field in ('id', 'title', 'summary', 'owner', 'next_decision', 'next_step', 'evidence_note', 'success_definition'):
                if not isinstance(goal[field], str):
                    raise ValueError('Invalid goal field')
            for field in ('stages', 'metric_keys'):
                if not isinstance(goal[field], list) or not all(isinstance(v, str) for v in goal[field]):
                    raise ValueError('Invalid goal references')
            if goal['target'] is not None and not isinstance(goal['target'], str):
                raise ValueError('Goal target must be a description or null')
            if goal['outcome'] is not None and not isinstance(goal['outcome'], str):
                raise ValueError('Goal outcome must be a description or null')
        return goals

    def projects(self):
        self.workspace_titles('projects.json', 'projects')  # Validate the seed boundary on each read.
        return self.project_store.listing()

    def cluster_briefs(self):
        return self.workspace_titles('cluster-briefs.json', 'briefs')

    def workspace_titles(self, filename, key):
        path = self.path / filename
        if not path.exists():
            return []
        if not path.resolve().is_relative_to(self.path):
            raise ValueError('Collection leaves workspace')
        source = json.loads(path.read_text())
        if source.get('schema_version') != 1 or source.get('profile_id') != self.profile['id']:
            raise ValueError('Collection does not match workspace')
        items = source.get(key)
        if not isinstance(items, list) or not all(
            isinstance(item, dict) and isinstance(item.get('title'), str)
            and item['title'].strip() for item in items
        ):
            raise ValueError('Collection entries must have nonempty titles')
        return [{'title': item['title']} for item in items]

    def ad_accounts(self):
        accounts = self.config.get('ad_accounts', [])
        if not isinstance(accounts, list):
            raise ValueError('Ad accounts must be a list')
        public = []
        for account in accounts:
            if not isinstance(account, dict) or not all(
                isinstance(account.get(field), str) and account[field].strip()
                for field in ('provider', 'account_id', 'url')
            ):
                raise ValueError('Ad account fields are required')
            url = urlsplit(account['url'])
            if url.scheme != 'https' or not url.hostname or url.username or url.password:
                raise ValueError('Ad account links must use HTTPS without credentials')
            public.append({field: account[field] for field in ('provider', 'account_id', 'url')})
        return public

    def measurement(self):
        path = self.path / 'measurement.json'
        if not path.exists():
            return None
        if not path.resolve().is_relative_to(self.path):
            raise ValueError('Measurement leaves workspace')
        result = json.loads(path.read_text())
        if (result.get('profile_id') != self.profile['id'] or
                result.get('profile_sha256') != self.profile_ref['sha256']):
            raise ValueError('Measurement does not match workspace')
        return result

    def dashboard(self):
        runs, rejected = [], 0
        root = self.path / 'runs'
        if not root.resolve().is_relative_to(self.path):
            raise ValueError('Run root leaves workspace')
        for folder in sorted(root.iterdir(), reverse=True):
            if not folder.is_dir():
                continue
            try:
                paths = [folder / 'manifest.json', folder / 'next-companies.json']
                if any(not p.resolve().is_relative_to(root.resolve()) for p in paths):
                    raise ValueError('Run leaves workspace')
                manifest_raw, result_raw = [p.read_bytes() for p in paths]
                manifest, result = json.loads(manifest_raw), json.loads(result_raw)
                if (result['profile_id'] != self.profile['id']
                        or result['profile_version'] != self.profile['version']
                        or result['funnel'] != self.profile['funnel']
                        or manifest['inputs']['profile']['sha256'] != self.profile_ref['sha256']
                        or manifest['output_sha256'] != hashlib.sha256(result_raw).hexdigest()
                        or manifest['run_id'] != result['run_id']):
                    raise ValueError('Run does not match pinned workspace')
                # Validate the result shape before making it available to the UI.
                for key in ('selected', 'reserves', 'excluded', 'coverage_gaps'):
                    if not isinstance(result[key], list):
                        raise ValueError('Invalid run')
                if not isinstance(manifest['created_at'], str):
                    raise ValueError('Invalid timestamp')
                # Local paths never need to cross the client boundary.
                public_manifest = {key: manifest[key] for key in
                                   ('run_id', 'created_at', 'status', 'output_sha256', 'execution')}
                public_manifest['input_hashes'] = {
                    name: manifest['inputs'][name]['sha256']
                    for name in ('profile', 'candidates', 'exclusions')}
                runs.append({'result': result, 'manifest': public_manifest})
            except (OSError, ValueError, KeyError, TypeError):
                rejected += 1
        runs.sort(key=lambda run: run['manifest']['created_at'], reverse=True)
        return {'client': {'name': self.profile['company'], 'synthetic': self.config['synthetic'],
                           'email': self.config['email'], 'timezone': self.config.get('timezone', 'UTC')},
                'profile': self.profile, 'runs': runs, 'unavailable_runs': rejected,
                'measurement': self.measurement(), 'goals': self.goals(), 'projects': self.projects(),
                'cluster_briefs': self.cluster_briefs(), 'ad_accounts': self.ad_accounts(),
                'served_at': datetime.now(timezone.utc).isoformat()}


class PortalServer(ThreadingHTTPServer):
    daemon_threads = True

    def __init__(self, workspace, port=8765, *, google_credentials=None, google_admin_emails=None, exa_key_file=None):
        self.workspace = Workspace(workspace)
        self.exa = ExaSearch(exa_key_file or self.workspace.path / 'exa-api-key.txt')
        self.google = None
        if google_credentials:
            from .adapters.google_identity import GoogleIdentity
            self.google = GoogleIdentity(google_credentials)
        if google_admin_emails is None:
            google_admin_emails = self.workspace.config.get('google_admin_emails', [])
        if not isinstance(google_admin_emails, (list, tuple)) or not all(isinstance(email, str) for email in google_admin_emails):
            raise ValueError('Google administrator emails must be a list of exact addresses')
        for email in google_admin_emails:
            if email.count('@') != 1 or any(c.isspace() for c in email):
                raise ValueError('Google administrator emails must be exact email addresses')
        self.workspace.access.admin_emails = frozenset(email.lower() for email in google_admin_emails)
        super().__init__(('127.0.0.1', port), Handler)
        self.origin = f'http://127.0.0.1:{self.server_port}'
        self.redirect_uri = self.origin + '/auth/google/callback'


class Handler(BaseHTTPRequestHandler):
    def setup(self):
        super().setup()
        self.connection.settimeout(10)

    def log_message(self, *_args):
        pass  # Do not put emails, tokens or client URLs in request logs.

    def respond(self, status, value, content_type='application/json', cookie=None, location=None):
        body = json.dumps(value).encode() if content_type == 'application/json' else value
        self.send_response(status)
        self.send_header('Content-Type', content_type + ('; charset=utf-8' if content_type.startswith('text/') or content_type == 'application/json' else ''))
        self.send_header('Content-Length', str(len(body)))
        self.send_header('Cache-Control', 'no-store')
        self.send_header('X-Content-Type-Options', 'nosniff')
        self.send_header('Referrer-Policy', 'no-referrer')
        self.send_header('Content-Security-Policy', "default-src 'self'; script-src 'self'; style-src 'self'; img-src 'self' data:; connect-src 'self'; frame-ancestors 'none'; base-uri 'none'; form-action 'self'")
        if location:
            self.send_header('Location', location)
        for item in ([cookie] if isinstance(cookie, str) else cookie or []):
            self.send_header('Set-Cookie', item)
        self.end_headers()
        self.wfile.write(body)

    def valid_host(self):
        return self.headers.get('Host') == urlsplit(self.server.origin).netloc

    def token(self, name='portal_session'):
        cookie = SimpleCookie()
        try:
            cookie.load(self.headers.get('Cookie', ''))
            return cookie[name].value if name in cookie else ''
        except Exception:
            return ''

    def do_GET(self):
        if not self.valid_host():
            return self.respond(403, {'error': 'Invalid host'})
        path = urlsplit(self.path).path
        assets = {'/': ('index.html', 'text/html'), '/app.js': ('app.js', 'text/javascript'),
                  '/style.css': ('style.css', 'text/css'), '/studio.css': ('studio.css', 'text/css'),
                  '/projects.js': ('projects.js', 'text/javascript'), '/projects.css': ('projects.css', 'text/css'),
                  '/logo.png': ('logo.png', 'image/png'),
                  '/design-system': ('design-system.html', 'text/html'),
                  '/design-system.html': ('design-system.html', 'text/html'),
                  '/design-tokens.css': ('design-tokens.css', 'text/css'),
                  '/components.css': ('components.css', 'text/css'),
                  '/portal-theme.css': ('portal-theme.css', 'text/css'),
                  '/design-system.css': ('design-system.css', 'text/css'),
                  '/design-system.js': ('design-system.js', 'text/javascript')}
        if path in assets:
            name, mime = assets[path]
            return self.respond(200, (ASSETS / name).read_bytes(), mime)
        if path == '/api/auth/config':
            return self.respond(200, {'google_enabled': self.server.google is not None})
        if path == '/auth/google/callback':
            return self.google_callback()
        if path == '/api/project':
            principal = self.server.workspace.access.principal(self.token())
            if not principal:
                return self.respond(401, {'error': 'Sign in to access your workspace'})
            try:
                query = parse_qs(urlsplit(self.path).query, max_num_fields=2, keep_blank_values=True)
                if set(query) != {'id'} or len(query['id']) != 1:
                    raise ValueError('Choose one project')
                store = self.server.workspace.project_store
                return self.respond(200, {'project': store.public(store.get(query['id'][0])),
                                          'exa_enabled': self.server.exa.enabled})
            except LookupError as error:
                return self.respond(404, {'error': str(error)})
            except ValueError as error:
                return self.respond(400, {'error': str(error)})
        if path == '/api/dashboard' and not urlsplit(self.path).query:
            principal = self.server.workspace.access.principal(self.token())
            if not principal:
                return self.respond(401, {'error': 'Sign in to access your workspace'})
            try:
                dashboard = self.server.workspace.dashboard()
                dashboard['client']['email'] = principal['email']
                dashboard['identity'] = {'email': principal['email'], 'role': principal['role'], 'provider': principal['provider']}
                if principal['role'] == 'admin':
                    dashboard['access'] = {**self.server.workspace.access.summary(),
                                           'google_enabled': self.server.google is not None,
                                           'redirect_uri': self.server.redirect_uri,
                                           'admin_emails': sorted(self.server.workspace.access.admin_emails)}
                return self.respond(200, dashboard)
            except (OSError, ValueError, TypeError, KeyError):
                return self.respond(503, {'error': 'Workspace unavailable. Contact your operator.'})
        self.respond(404, {'error': 'Not found'})

    def do_POST(self):
        if not self.valid_host() or self.headers.get('Origin') != self.server.origin:
            return self.respond(403, {'error': 'Invalid request origin'})
        project_routes = ('/api/project/record/remove', '/api/project/record/restore', '/api/project/contact/add', '/api/project/contact/update', '/api/project/target/add', '/api/project/target/update', '/api/project/search',
                          '/api/project/clusters', '/api/project/assets')
        if self.path not in ('/api/login', '/api/logout', '/api/auth/google', '/api/admin/domains') + project_routes:
            return self.respond(404, {'error': 'Not found'})
        try:
            length = int(self.headers.get('Content-Length', '0'))
            if not 0 < length <= (65536 if self.path in project_routes else 4096) or self.headers.get('Content-Type') != 'application/json':
                raise ValueError('Invalid body')
            data = json.loads(self.rfile.read(length))
            if not isinstance(data, dict):
                raise ValueError('Invalid body')
        except (ValueError, OSError):
            return self.respond(400, {'error': 'Invalid request'})
        if self.path in project_routes:
            actor = self.server.workspace.access.principal(self.token())
            if actor is None:
                return self.respond(401, {'error': 'Sign in to access your workspace'})
            store = self.server.workspace.project_store
            project_id = data.get('project_id')
            try:
                if any(key in data for key in ('workspace', 'client', 'client_id', 'workspace_id')):
                    raise ValueError('Project actions use your signed-in workspace')
                if self.path == '/api/project/search':
                    project = store.run_search(project_id, data, actor['email'], self.server.exa)
                elif self.path == '/api/project/clusters':
                    project = store.run_clustering(project_id, actor['email'])
                else:
                    method = {'/api/project/record/remove': store.remove_record,
                              '/api/project/record/restore': store.restore_record,
                              '/api/project/contact/add': store.add_contact,
                              '/api/project/contact/update': store.update_contact,
                              '/api/project/target/add': store.add_target,
                              '/api/project/target/update': store.update_target,
                              '/api/project/assets': store.add_asset}[self.path]
                    project = method(project_id, data, actor['email'])
                return self.respond(200, {'project': store.public(project), 'projects': store.listing(),
                                          'exa_enabled': self.server.exa.enabled})
            except LookupError as error:
                return self.respond(404, {'error': str(error)})
            except (ValueError, TypeError) as error:
                return self.respond(400, {'error': str(error)})
        if self.path == '/api/auth/google':
            if self.server.google is None:
                return self.respond(503, {'error': 'Google sign-in has not been configured yet.'})
            try:
                flow = self.server.workspace.access.begin_flow()
                return self.respond(200, {'url': self.server.google.authorization_url(self.server.redirect_uri, flow)},
                                    cookie=f"portal_oauth={flow['browser']}; HttpOnly; SameSite=Lax; Path=/auth/google/callback; Max-Age=600")
            except ValueError as error:
                return self.respond(429, {'error': str(error)})
        if self.path == '/api/admin/domains':
            access = self.server.workspace.access
            actor = access.principal(self.token())
            if actor is None:
                return self.respond(401, {'error': 'Sign in to manage workspace access'})
            try:
                result = access.change_domain(actor, data.get('action'), data.get('domain'))
                return self.respond(200, result)
            except PermissionError as error:
                return self.respond(403, {'error': str(error)})
            except ValueError as error:
                return self.respond(400, {'error': str(error)})
        if self.path == '/api/logout':
            self.server.workspace.logout(self.token())
            return self.respond(200, {'ok': True}, cookie='portal_session=; HttpOnly; SameSite=Strict; Path=/; Max-Age=0')
        email, password = data.get('email'), data.get('password')
        if not isinstance(email, str) or not isinstance(password, str):
            return self.respond(400, {'error': 'Email and password are required'})
        token, status = self.server.workspace.login(email, password)
        if status != 200:
            return self.respond(status, {'error': 'Too many attempts. Try again in five minutes.' if status == 429 else 'Email or password is incorrect.'})
        self.respond(200, {'ok': True}, cookie=f'portal_session={token}; HttpOnly; SameSite=Strict; Path=/; Max-Age={SESSION_SECONDS}')

    def google_callback(self):
        clear = 'portal_oauth=; HttpOnly; SameSite=Lax; Path=/auth/google/callback; Max-Age=0'
        try:
            if self.server.google is None:
                raise ValueError('Not configured')
            query = parse_qs(urlsplit(self.path).query, max_num_fields=20)
            if any(len(values) != 1 for values in query.values()):
                raise ValueError('Ambiguous callback')
            flow = self.server.workspace.access.consume_flow(query.get('state', [''])[0], self.token('portal_oauth'))
            if 'error' in query:
                return self.respond(303, {}, cookie=clear, location='/?auth_error=cancelled')
            code = query.get('code', [''])[0]
            if not code or len(code) > 4096:
                raise ValueError('Missing code')
            identity = self.server.google.authenticate(code, self.server.redirect_uri, flow)
        except ValueError:
            return self.respond(303, {}, cookie=clear, location='/?auth_error=verification')
        try:
            token = self.server.workspace.access.google_session(identity)
        except ValueError:
            return self.respond(303, {}, cookie=clear, location='/?auth_error=access')
        self.server.workspace.logout(self.token())
        return self.respond(303, {}, cookie=[clear,
            f'portal_session={token}; HttpOnly; SameSite=Strict; Path=/; Max-Age={SESSION_SECONDS}'], location='/#overview')


def main(argv=None):
    parser = argparse.ArgumentParser(description='Local single-client GTM portal')
    commands = parser.add_subparsers(dest='command', required=True)
    init = commands.add_parser('init', help='Provision an isolated client workspace')
    init.add_argument('--workspace', required=True)
    init.add_argument('--profile', required=True)
    init.add_argument('--email', required=True)
    init.add_argument('--synthetic', action='store_true')
    demo = commands.add_parser('demo', help='Create a labeled synthetic workspace')
    demo.add_argument('--workspace', default='private/portal-demo')
    demo.add_argument('--example', default='examples/warehouse-software')
    serve = commands.add_parser('serve', help='Serve locally on 127.0.0.1')
    serve.add_argument('--workspace', required=True)
    serve.add_argument('--port', type=int, default=8765)
    serve.add_argument('--exa-key-file', help='Private file containing an Exa API key; otherwise use EXA_API_KEY or workspace/exa-api-key.txt')
    serve.add_argument('--google-credentials', help='Private Google OAuth web client JSON')
    serve.add_argument('--google-admin-email', action='append', help='Exact trusted agency Google email; repeat for additional admins')
    args = parser.parse_args(argv)
    try:
        if args.command == 'init':
            initialize(args.workspace, args.profile, args.email, getpass.getpass('Client password: '), synthetic=args.synthetic)
            print('Workspace created. Generate client runs into its runs/ directory.')
        elif args.command == 'demo':
            source = Path(args.example)
            password = secrets.token_urlsafe(18)
            workspace = initialize(args.workspace, source / 'profile.json', 'client@example.test', password, synthetic=True)
            for name in ('candidates', 'exclusions'):
                shutil.copyfile(source / f'{name}.json', workspace / f'{name}.json')
            values, refs = {}, {}
            for name in ('profile', 'candidates', 'exclusions'):
                values[name], refs[name] = load(workspace / f'{name}.json')
            write_run(select(values['profile'], values['candidates'], values['exclusions'], 2,
                             values['exclusions']['as_of']), refs, workspace / 'runs')
            credentials = workspace / 'demo-login.txt'
            credentials.write_text(f'Synthetic demo only\nEmail: client@example.test\nPassword: {password}\n')
            credentials.chmod(0o600)
            print(f'Synthetic workspace created. Login details: {credentials}')
        else:
            server = PortalServer(args.workspace, args.port, google_credentials=args.google_credentials,
                                  google_admin_emails=args.google_admin_email, exa_key_file=args.exa_key_file)
            print(f'Client portal: {server.origin}', flush=True)
            try:
                server.serve_forever()
            except KeyboardInterrupt:
                pass
            finally:
                server.server_close()
        return 0
    except (OSError, ValueError, KeyError) as error:
        parser.exit(2, f'Error: {error}\n')


if __name__ == '__main__':
    raise SystemExit(main())
