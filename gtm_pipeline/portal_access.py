"""Workspace access policy and revocable identities, independent of providers."""

import hashlib
import json
import re
import secrets
import time

SESSION_SECONDS = 8 * 60 * 60


def fingerprint(value):
    return hashlib.sha256(value.encode()).hexdigest()


def normalize_domain(value):
    if not isinstance(value, str):
        raise ValueError('Enter a company domain, such as example.com')
    value = value.strip().lower()
    if len(value) > 253 or '.' not in value or not all(
        re.fullmatch(r'[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?', label)
        for label in value.split('.')
    ) or value.replace('.', '').isdigit():
        raise ValueError('Enter only a domain, without a URL, email address or wildcard')
    return value


class Access:
    def __init__(self, workspace):
        self.workspace = workspace
        self.connect = workspace.connect
        self.admin_emails = frozenset()
        with self.connect() as db:
            columns = {row[1] for row in db.execute('PRAGMA table_info(sessions)')}
            if 'identity' not in columns:
                db.execute('ALTER TABLE sessions ADD COLUMN identity TEXT')
                # Legacy sessions did not distinguish client and operator roles.
                db.execute('DELETE FROM sessions')
            db.execute('CREATE TABLE IF NOT EXISTS domains (domain TEXT PRIMARY KEY, created REAL, actor TEXT)')
            db.execute('CREATE TABLE IF NOT EXISTS admin_bindings (email TEXT PRIMARY KEY, subject TEXT UNIQUE)')
            db.execute('CREATE TABLE IF NOT EXISTS access_events (at REAL, actor TEXT, action TEXT, domain TEXT)')
            db.execute('CREATE TABLE IF NOT EXISTS auth_flows (state TEXT PRIMARY KEY, browser TEXT, nonce TEXT, verifier TEXT, expires REAL)')

    def create_session(self, identity, db=None):
        token = secrets.token_urlsafe(32)
        def insert(connection):
            connection.execute('DELETE FROM sessions WHERE expires < ?', (time.time(),))
            connection.execute('INSERT INTO sessions(token, expires, identity) VALUES (?, ?, ?)',
                               (fingerprint(token), time.time() + SESSION_SECONDS, json.dumps(identity)))
        if db is None:
            with self.connect() as connection:
                insert(connection)
        else:
            insert(db)
        return token

    def local_session(self):
        return self.create_session({'provider': 'local', 'email': self.workspace.config['email'], 'role': 'admin'})

    def google_session(self, identity):
        """Accept only an identity already verified by the Google adapter."""
        email, subject, domain = identity['email'], identity['subject'], identity['domain']
        with self.connect() as db:
            db.execute('BEGIN IMMEDIATE')
            role = 'client'
            if email in self.admin_emails:
                binding = db.execute('SELECT subject FROM admin_bindings WHERE email = ?', (email,)).fetchone()
                if binding and binding[0] != subject:
                    raise ValueError('Agency identity has changed. Contact your operator.')
                if not binding:
                    db.execute('INSERT INTO admin_bindings VALUES (?, ?)', (email, subject))
                role = 'admin'
            elif not domain or not db.execute('SELECT 1 FROM domains WHERE domain = ?', (domain,)).fetchone():
                raise ValueError('Your company has not been granted access to this workspace.')
            return self.create_session({**identity, 'provider': 'google', 'role': role}, db)

    def principal(self, token):
        with self.connect() as db:
            row = db.execute('SELECT identity FROM sessions WHERE token = ? AND expires > ?',
                             (fingerprint(token), time.time())).fetchone()
            if not row or not row[0]:
                return None
            identity = json.loads(row[0])
            if identity['provider'] == 'google':
                if identity['role'] == 'admin':
                    binding = db.execute('SELECT subject FROM admin_bindings WHERE email = ?', (identity['email'],)).fetchone()
                    if identity['email'] not in self.admin_emails or not binding or binding[0] != identity['subject']:
                        return None
                elif not db.execute('SELECT 1 FROM domains WHERE domain = ?', (identity['domain'],)).fetchone():
                    return None
            return identity

    def summary(self):
        with self.connect() as db:
            domains = [{'domain': row[0], 'created_at': row[1]} for row in
                       db.execute('SELECT domain, created FROM domains ORDER BY domain')]
            events = [{'at': row[0], 'actor': row[1], 'action': row[2], 'domain': row[3]} for row in
                      db.execute('SELECT at, actor, action, domain FROM access_events ORDER BY rowid DESC LIMIT 10')]
        return {'domains': domains, 'events': events}

    def change_domain(self, actor, action, value):
        if actor is None or actor.get('role') != 'admin':
            raise PermissionError('Agency administrator access is required')
        domain = normalize_domain(value)
        if action not in ('add', 'remove'):
            raise ValueError('Choose add or remove')
        with self.connect() as db:
            db.execute('BEGIN IMMEDIATE')
            if action == 'add':
                changed = db.execute('INSERT OR IGNORE INTO domains VALUES (?, ?, ?)',
                                     (domain, time.time(), actor['email'])).rowcount
            else:
                changed = db.execute('DELETE FROM domains WHERE domain = ?', (domain,)).rowcount
                # Delete existing client sessions so re-adding a domain cannot revive them.
                for token, raw in db.execute('SELECT token, identity FROM sessions').fetchall():
                    identity = json.loads(raw)
                    if identity.get('provider') == 'google' and identity.get('role') == 'client' and identity.get('domain') == domain:
                        db.execute('DELETE FROM sessions WHERE token = ?', (token,))
            if changed:
                db.execute('INSERT INTO access_events VALUES (?, ?, ?, ?)', (time.time(), actor['email'], action, domain))
        return self.summary()

    def begin_flow(self):
        state, browser, nonce, verifier = (secrets.token_urlsafe(32) for _ in range(4))
        with self.connect() as db:
            db.execute('BEGIN IMMEDIATE')
            db.execute('DELETE FROM auth_flows WHERE expires < ?', (time.time(),))
            if db.execute('SELECT count(*) FROM auth_flows').fetchone()[0] >= 100:
                raise ValueError('Too many sign-in attempts. Try again in ten minutes.')
            db.execute('INSERT INTO auth_flows VALUES (?, ?, ?, ?, ?)',
                       (fingerprint(state), fingerprint(browser), nonce, verifier, time.time() + 600))
        return {'state': state, 'browser': browser, 'nonce': nonce, 'verifier': verifier}

    def consume_flow(self, state, browser):
        with self.connect() as db:
            db.execute('BEGIN IMMEDIATE')
            row = db.execute('SELECT nonce, verifier FROM auth_flows WHERE state = ? AND browser = ? AND expires > ?',
                             (fingerprint(state), fingerprint(browser), time.time())).fetchone()
            if not row:
                raise ValueError('Sign-in expired or was opened in another browser. Please try again.')
            db.execute('DELETE FROM auth_flows WHERE state = ?', (fingerprint(state),))
        return {'nonce': row[0], 'verifier': row[1]}
