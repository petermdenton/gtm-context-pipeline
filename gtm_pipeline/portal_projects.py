"""Persistent project targets, search provenance, cluster snapshots and draft assets."""

from contextlib import contextmanager
from datetime import datetime, timezone
import hashlib
import ipaddress
import json
from pathlib import Path
import re
import sqlite3
from urllib.parse import urlsplit, urlunsplit
from uuid import uuid4

from .project_clustering import cluster, input_hash
from .adapters.exa_search import normalize_results


def now():
    return datetime.now(timezone.utc).isoformat()


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, allow_nan=False).encode()).hexdigest()


def text(value, label, maximum, required=False):
    if not isinstance(value, str) or len(value) > maximum or (required and not value.strip()):
        raise ValueError(f'{label} must be {"nonempty and " if required else ""}at most {maximum} characters')
    return value.strip()


def website(value):
    value = text(value, 'Website', 2000, True)
    if any(c.isspace() or ord(c) < 32 for c in value):
        raise ValueError('Website must not contain whitespace')
    if '://' not in value:
        value = 'https://' + value
    parts = urlsplit(value)
    host = (parts.hostname or '').lower().removeprefix('www.')
    if parts.scheme not in ('http', 'https') or not host or parts.username or parts.password or parts.port not in (None, 80, 443):
        raise ValueError('Enter a company website without credentials or a custom port')
    try:
        ipaddress.ip_address(host)
    except ValueError:
        pass
    else:
        raise ValueError('Use a company domain, not an IP address')
    if '.' not in host or not all(re.fullmatch(r'[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?', label) for label in host.split('.')):
        raise ValueError('Enter a valid company domain')
    return host, urlunsplit((parts.scheme, parts.netloc.lower(), parts.path, parts.query, ''))


def target_fields(body):
    domain, url = website(body.get('website'))
    tags = body.get('tags', [])
    if not isinstance(tags, list) or len(tags) > 20:
        raise ValueError('Use at most 20 tags')
    return {'name': text(body.get('name'), 'Company name', 200, True), 'domain': domain, 'url': url,
            'description': text(body.get('description', ''), 'Description', 6000),
            'sector': text(body.get('sector', ''), 'Sector', 150),
            'tags': list(dict.fromkeys(text(tag, 'Tag', 80, True).lower() for tag in tags)),
            'notes': text(body.get('notes', ''), 'Notes', 6000)}


def contact_fields(body):
    email = text(body.get('email', ''), 'Email', 254).lower()
    if email and not re.fullmatch(r"[^\s@<>]+@[^\s@<>]+\.[^\s@<>]+", email):
        raise ValueError('Enter a valid email address or leave it blank')
    profile_url = text(body.get('profile_url', ''), 'Profile URL', 2000)
    if profile_url:
        _, profile_url = website(profile_url)
        profile_url = profile_url.rstrip('/')
    return {'name': text(body.get('name'), 'Contact name', 200, True),
            'company': text(body.get('company', ''), 'Company', 200),
            'role': text(body.get('role', ''), 'Role', 200), 'email': email,
            'profile_url': profile_url, 'notes': text(body.get('notes', ''), 'Notes', 6000)}


class ProjectStore:
    def __init__(self, workspace):
        self.workspace = workspace
        self.path = workspace.path / 'projects.sqlite3'
        if not self.path.resolve().is_relative_to(workspace.path):
            raise ValueError('Project database leaves workspace')
        with self.connect() as db:
            db.execute('CREATE TABLE IF NOT EXISTS projects (id TEXT PRIMARY KEY, seed_key TEXT UNIQUE, document TEXT NOT NULL)')
            seeds = workspace.workspace_titles('projects.json', 'projects')
            for seed in seeds:
                key = digest({'profile': workspace.profile['id'], 'title': seed['title']})
                if db.execute('SELECT 1 FROM projects WHERE seed_key = ?', (key,)).fetchone():
                    continue
                project = {'id': uuid4().hex, 'title': seed['title'], 'created_at': now(), 'updated_at': now(),
                           'revision': 0, 'targets': [], 'contacts': [], 'source_imports': [], 'searches': [], 'cluster_runs': [], 'assets': [], 'events': []}
                db.execute('INSERT INTO projects VALUES (?, ?, ?)', (project['id'], key, json.dumps(project)))
        self.path.chmod(0o600)

    @contextmanager
    def connect(self):
        db = sqlite3.connect(self.path, timeout=10)
        try:
            with db:
                yield db
        finally:
            db.close()

    def _get(self, db, project_id):
        if not isinstance(project_id, str):
            raise ValueError('Choose a project')
        row = db.execute('SELECT document FROM projects WHERE id = ?', (project_id,)).fetchone()
        if not row:
            raise LookupError('Project not found in this workspace')
        project = json.loads(row[0])
        project.setdefault('contacts', [])
        project.setdefault('source_imports', [])
        project.setdefault('removed_records', [])
        return project

    def get(self, project_id):
        with self.connect() as db:
            return self._get(db, project_id)

    def public(self, project):
        value = json.loads(json.dumps(project))
        searches = {run['id'] for run in project['searches'] if run['status'] == 'completed'}
        imports = {event['id']: event['kind'] for event in project.get('source_imports', [])
                   if event['status'] == 'completed'}
        counts = {'searches': 0, 'upload': 0, 'mcp': 0}
        for record in project['targets'] + project.get('contacts', []):
            kinds = set()
            for source in record.get('sources', []):
                if source['kind'] == 'exa' and source.get('search_id') in searches:
                    kinds.add('searches')
                elif source['kind'] in ('upload', 'mcp') and imports.get(source.get('import_id')) == source['kind']:
                    kinds.add(source['kind'])
            for kind in kinds:
                counts[kind] += 1
        value['source_usage'] = {kind: count > 0 for kind, count in counts.items()}
        value['source_record_counts'] = counts
        for search in value['searches']:
            search.pop('raw_response', None)
        current_hash = input_hash(value['targets'])
        for run in value['cluster_runs']:
            run['stale'] = run['input_hash'] != current_hash
        return value

    def listing(self):
        with self.connect() as db:
            values = [json.loads(row[0]) for row in db.execute('SELECT document FROM projects ORDER BY rowid')]
        return [{'id': p['id'], 'title': p['title'], 'target_count': len(p['targets']) + len(p.get('contacts', [])),
                 'company_count': len(p['targets']), 'contact_count': len(p.get('contacts', [])),
                 'search_count': len(p['searches']), 'updated_at': p['updated_at']} for p in values]

    def mutate(self, project_id, actor, action, callback):
        with self.connect() as db:
            db.execute('BEGIN IMMEDIATE')
            project = self._get(db, project_id)
            callback(project)
            project['revision'] += 1
            project['updated_at'] = now()
            project['events'].append({'at': now(), 'actor': actor, 'action': action})
            db.execute('UPDATE projects SET document = ? WHERE id = ?',
                       (json.dumps(project, allow_nan=False), project_id))
            return project

    def add_target(self, project_id, body, actor):
        fields = target_fields(body)
        def add(project):
            if len(project['targets']) >= 1000:
                raise ValueError('This project has reached its 1,000-target limit')
            if any(t['domain'] == fields['domain'] for t in project['targets']):
                raise ValueError('That domain is already in this project')
            project['targets'].append({**fields, 'id': uuid4().hex, 'created_at': now(), 'updated_at': now(),
                                       'review_status': 'unreviewed', 'sources': [{'kind': 'manual', 'at': now(), 'actor': actor, 'fields': fields}]})
        return self.mutate(project_id, actor, 'target.add', add)

    def update_target(self, project_id, body, actor):
        fields = target_fields(body)
        def update(project):
            target = next((t for t in project['targets'] if t['id'] == body.get('target_id')), None)
            if not target:
                raise LookupError('Target not found in this project')
            if any(t['domain'] == fields['domain'] and t['id'] != target['id'] for t in project['targets']):
                raise ValueError('That domain is already in this project')
            target['sources'].append({'kind': 'manual-edit', 'at': now(), 'actor': actor, 'fields': fields,
                                      'previous': {key: target[key] for key in fields}})
            target.update(fields)
            target['updated_at'] = now()
        return self.mutate(project_id, actor, 'target.update', update)

    def add_contact(self, project_id, body, actor):
        return self.save_contact(project_id, body, actor, editing=False)

    def update_contact(self, project_id, body, actor):
        return self.save_contact(project_id, body, actor, editing=True)

    def save_contact(self, project_id, body, actor, *, editing):
        fields = contact_fields(body)
        def save(project):
            contact = next((c for c in project['contacts'] if c['id'] == body.get('contact_id')), None) if editing else None
            if editing and contact is None:
                raise LookupError('Contact not found in this project')
            if not editing and len(project['contacts']) >= 1000:
                raise ValueError('This project has reached its 1,000-contact limit')
            for existing in project['contacts']:
                if contact and existing['id'] == contact['id']:
                    continue
                if ((fields['email'] and fields['email'] == existing['email']) or
                        (fields['profile_url'] and fields['profile_url'] == existing['profile_url'])):
                    raise ValueError('A contact with that email or profile is already in this project')
            if editing:
                contact['sources'].append({'kind': 'manual-edit', 'at': now(), 'actor': actor, 'fields': fields,
                                            'previous': {key: contact[key] for key in fields}})
                contact.update(fields)
                contact['updated_at'] = now()
            else:
                project['contacts'].append({**fields, 'id': uuid4().hex, 'created_at': now(), 'updated_at': now(),
                                            'review_status': 'unreviewed',
                                            'sources': [{'kind': 'manual', 'at': now(), 'actor': actor, 'fields': fields}]})
        return self.mutate(project_id, actor, 'contact.update' if editing else 'contact.add', save)

    def remove_record(self, project_id, body, actor):
        kind, record_id = body.get('record_type'), body.get('record_id')
        if kind not in ('company', 'contact'):
            raise ValueError('Choose a company or contact')
        def remove(project):
            collection = project['targets'] if kind == 'company' else project['contacts']
            record = next((record for record in collection if record['id'] == record_id), None)
            if record is None:
                raise LookupError('Record not found in this project')
            collection.remove(record)
            project['removed_records'].append({'id': uuid4().hex, 'record_type': kind, 'record': record,
                                               'removed_at': now(), 'removed_by': actor})
        return self.mutate(project_id, actor, kind + '.remove', remove)

    def restore_record(self, project_id, body, actor):
        def restore(project):
            archived = next((entry for entry in project['removed_records'] if entry['id'] == body.get('removed_id')), None)
            if archived is None:
                raise LookupError('Removed record not found in this project')
            record, kind = archived['record'], archived['record_type']
            collection = project['targets'] if kind == 'company' else project['contacts']
            if len(collection) >= 1000:
                raise ValueError('The project record limit must be reduced before restoring')
            for existing in collection:
                duplicate = existing['id'] == record['id']
                if kind == 'company':
                    duplicate = duplicate or existing['domain'] == record['domain']
                else:
                    duplicate = duplicate or (record['email'] and existing['email'] == record['email']) or (
                        record['profile_url'] and existing['profile_url'] == record['profile_url'])
                if duplicate:
                    raise ValueError('A matching record already exists in this project. Review it before restoring.')
            collection.append(record)
            project['removed_records'].remove(archived)
            project['events'].append({'at': now(), 'actor': actor, 'action': kind + '.restored',
                                      'record_id': record['id'], 'removed_at': archived['removed_at'],
                                      'removed_by': archived['removed_by']})
        return self.mutate(project_id, actor, 'record.restore', restore)

    def import_source_records(self, project_id, *, kind, label, records, actor, operation_id):
        """Local adapter boundary for supplied records; does not upload or connect to MCP.

        Source receipts and records commit together. Labels are display names, not
        credential-bearing connection URLs. Repeating an operation is idempotent.
        """
        if kind not in ('upload', 'mcp'):
            raise ValueError('Choose upload or mcp provenance')
        label = text(label, 'Source name', 200, True)
        operation_id = text(operation_id, 'Operation ID', 80, True)
        if not isinstance(records, list) or len(records) > 1000:
            raise ValueError('Supply at most 1,000 records per import')
        normalized = []
        for record in records:
            if not isinstance(record, dict) or record.get('record_type') not in ('company', 'contact'):
                raise ValueError('Each import record must specify company or contact')
            fields = target_fields(record) if record['record_type'] == 'company' else contact_fields(record)
            normalized.append((record['record_type'], fields))
        def ingest(project):
            if any(event['operation_id'] == operation_id for event in project['source_imports']):
                return
            event_id, at, contributions = uuid4().hex, now(), []
            for record_type, fields in normalized:
                collection = project['targets'] if record_type == 'company' else project['contacts']
                if record_type == 'company':
                    target = next((t for t in collection if t['domain'] == fields['domain']), None)
                else:
                    matches = [t for t in collection if (fields['email'] and t['email'] == fields['email']) or
                               (fields['profile_url'] and t['profile_url'] == fields['profile_url'])]
                    if len(matches) > 1:
                        raise ValueError('Conflicting contact identities require review before importing')
                    target = matches[0] if matches else None
                action = 'evidence_added' if target else 'added'
                source = {'kind': kind, 'import_id': event_id, 'label': label, 'at': at, 'actor': actor}
                if target:
                    target['sources'].append(source)
                else:
                    if len(collection) >= 1000:
                        raise ValueError('An import would exceed the project record limit')
                    target = {**fields, 'id': uuid4().hex, 'created_at': at, 'updated_at': at,
                              'review_status': 'unreviewed', 'sources': [source]}
                    collection.append(target)
                contributions.append({'record_type': record_type, 'record_id': target['id'],
                                      'action': action, 'fields': fields})
            project['source_imports'].append({'id': event_id, 'kind': kind, 'label': label, 'actor': actor,
                                              'at': at, 'status': 'completed', 'operation_id': operation_id,
                                              'input_hash': digest(records), 'contributions': contributions})
        return self.mutate(project_id, actor, 'source.' + kind + '.import', ingest)

    def run_search(self, project_id, body, actor, adapter):
        if not adapter.enabled:
            raise ValueError('Exa is not connected. Manual targets are available now.')
        operation = text(body.get('operation_id'), 'Operation ID', 80, True)
        previous = self.get(project_id)
        existing = next((run for run in previous['searches'] if run['operation_id'] == operation), None)
        if existing:
            return previous
        rerun_id = body.get('rerun_id')
        if rerun_id:
            original = next((run for run in previous['searches'] if run['id'] == rerun_id), None)
            if not original:
                raise LookupError('Search not found in this project')
            parameters = original['parameters']
        else:
            query = text(body.get('query'), 'Search query', 2000, True)
            count = body.get('num_results', 10)
            if type(count) is not int or not 1 <= count <= 100:
                raise ValueError('Request between 1 and 100 results')
            parameters = {'query': query, 'numResults': count, 'type': 'auto', 'category': 'company',
                          'contents': {'highlights': True}, 'moderation': True}
        run_id = uuid4().hex
        reserved = False
        def reserve(project):
            nonlocal reserved
            if any(run['operation_id'] == operation for run in project['searches']):
                return
            timestamp = datetime.now(timezone.utc)
            for run in project['searches']:
                if run['status'] == 'running':
                    elapsed = (timestamp - datetime.fromisoformat(run['started_at'])).total_seconds()
                    if elapsed < 120:
                        raise ValueError('A search is already running in this project')
                    run['status'] = 'unknown'
                    run['error'] = 'Search was interrupted. Check Exa usage before starting another run.'
            if sum((timestamp - datetime.fromisoformat(run['started_at'])).total_seconds() < 3600 for run in project['searches']) >= 20:
                raise ValueError('This project has reached 20 search attempts this hour')
            if len(project['targets']) >= 1000:
                raise ValueError('This project has reached its 1,000-target limit')
            project['searches'].append({'id': run_id, 'operation_id': operation, 'provider': 'Exa', 'parameters': parameters,
                                        'input_hash': digest(parameters), 'rerun_of': rerun_id, 'status': 'running',
                                        'started_at': now(), 'actor': actor})
            reserved = True
        project = self.mutate(project_id, actor, 'search.start', reserve)
        if not reserved:
            return project
        try:
            raw = adapter.search(parameters)
            results, rejected = normalize_results(raw)
            normalized = []
            for result in results:
                try:
                    normalized.append((target_fields(result), result['source_excerpt']))
                except (ValueError, TypeError):
                    rejected.append('Result requires company website review')
            def finish(project):
                run = next(run for run in project['searches'] if run['id'] == run_id)
                added, duplicates, omitted = 0, 0, len(rejected)
                target_ids, contributions = [], []
                for fields, excerpt in normalized:
                    target = next((t for t in project['targets'] if t['domain'] == fields['domain']), None)
                    source = {'kind': 'exa', 'search_id': run_id, 'url': fields['url'], 'at': now(), 'actor': actor, 'excerpt': excerpt}
                    disposition = 'evidence_added' if target else 'added'
                    if target:
                        duplicates += 1
                        target['sources'].append(source)
                    elif len(project['targets']) >= 1000:
                        omitted += 1
                        continue
                    else:
                        target = {**fields, 'id': uuid4().hex, 'created_at': now(), 'updated_at': now(),
                                  'review_status': 'unreviewed', 'sources': [source]}
                        project['targets'].append(target)
                        added += 1
                    target_ids.append(target['id'])
                    contributions.append({'record_type': 'company', 'record_id': target['id'],
                                          'action': disposition, 'fields': fields, 'source_excerpt': excerpt})
                run.update({'status': 'completed', 'finished_at': now(), 'added': added, 'duplicates': duplicates,
                            'omitted': omitted, 'rejection_reasons': rejected, 'target_ids': target_ids, 'contributions': contributions,
                            'result_count': len(raw['results']), 'response_hash': digest(raw), 'raw_response': raw,
                            'provider_request_id': raw.get('requestId'), 'cost_dollars': raw.get('costDollars')})
            return self.mutate(project_id, actor, 'search.complete', finish)
        except Exception:
            def fail(project):
                run = next(run for run in project['searches'] if run['id'] == run_id)
                run.update({'status': 'failed', 'finished_at': now(),
                            'error': 'Search did not complete. Check the Exa connection and provider usage before retrying. No automatic retry was made.'})
            return self.mutate(project_id, actor, 'search.failed', fail)

    def run_clustering(self, project_id, actor):
        def run(project):
            if len(project['targets']) < 2:
                raise ValueError('Add at least two targets with descriptions, sectors or tags before clustering')
            result = cluster(project['targets'])
            project['cluster_runs'].append({**result, 'id': uuid4().hex, 'created_at': now(), 'actor': actor})
        return self.mutate(project_id, actor, 'clusters.run', run)

    def add_asset(self, project_id, body, actor):
        kind = body.get('kind')
        if kind not in ('brief', 'creative', 'landing_page'):
            raise ValueError('Choose a brief, creative or landing page')
        title = text(body.get('title'), 'Title', 200, True)
        content = text(body.get('body', ''), 'Content', 16000)
        url = text(body.get('url', ''), 'Source URL', 2000)
        if url:
            _, url = website(url)
        if not content and not url:
            raise ValueError('Add content or a source link')
        def add(project):
            run_id, cluster_id = body.get('cluster_run_id'), body.get('cluster_id')
            if kind == 'brief' and not cluster_id:
                raise ValueError('Choose the cluster this brief belongs to')
            if cluster_id:
                run = next((run for run in project['cluster_runs'] if run['id'] == run_id), None)
                if not run or not any(group['id'] == cluster_id for group in run['clusters']):
                    raise ValueError('Choose a cluster from this project')
            project['assets'].append({'id': uuid4().hex, 'kind': kind, 'title': title, 'body': content, 'url': url,
                                      'cluster_run_id': run_id, 'cluster_id': cluster_id, 'status': 'draft',
                                      'created_at': now(), 'actor': actor})
        return self.mutate(project_id, actor, kind + '.add', add)
