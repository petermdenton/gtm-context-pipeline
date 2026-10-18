"""Offline project behavior, persistence and authorization using synthetic companies."""
import http.client
import io
from urllib.error import HTTPError
import json
from pathlib import Path
import tempfile
import threading
import unittest
from unittest.mock import Mock, patch

from gtm_pipeline.portal import initialize, PortalServer, Workspace
from gtm_pipeline.portal_projects import ProjectStore, website
from gtm_pipeline.project_clustering import cluster, input_hash
from gtm_pipeline.adapters.exa_search import normalize_results, ExaSearch, ExaError

ROOT = Path(__file__).resolve().parents[1]
ACTOR = 'operator@example.test'


class ProjectTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.path = initialize(Path(self.temp.name) / 'client', ROOT / 'examples/warehouse-software/profile.json',
                               ACTOR, 'synthetic-password', synthetic=True)
        (self.path / 'projects.json').write_text(json.dumps({'schema_version': 1, 'profile_id': 'warehouse-software',
                                                          'projects': [{'title': 'Synthetic energy'}, {'title': 'Synthetic retail'}]}))
        self.workspace = Workspace(self.path)
        self.store = self.workspace.project_store
        self.pid, self.other = [p['id'] for p in self.store.listing()]
        self.adapter = Mock(enabled=True)
        self.adapter.search.return_value = {'requestId': 'synthetic-request', 'results': [
            {'title': 'Synthetic Grid', 'url': 'https://www.grid.example.test/about',
             'highlights': ['Renewable energy solar grid storage']},
            {'title': 'Synthetic Battery', 'url': 'https://battery.example.test',
             'highlights': ['Renewable energy solar grid storage']},
            {'title': 'Directory', 'url': 'https://linkedin.com/company/synthetic'}]}

    def tearDown(self):
        self.temp.cleanup()

    def add(self, domain='grid.example.test', **fields):
        return self.store.add_target(self.pid, {'name': 'Synthetic Grid', 'website': domain, **fields}, ACTOR)

    def search(self, operation='synthetic-one', **fields):
        return self.store.run_search(self.pid, {'operation_id': operation, 'query': 'Synthetic energy companies', **fields}, ACTOR, self.adapter)

    def test_stable_projects_manual_edit_dedup_and_restart(self):
        original = self.add(description='Manual assessment', tags=['Energy'])['targets'][0]
        with self.assertRaises(ValueError):
            self.add('https://www.grid.example.test/about')
        updated = self.store.update_target(self.pid, {'target_id': original['id'], 'name': original['name'],
                                                     'website': original['url'], 'description': 'Revised evidence'}, ACTOR)
        restarted = Workspace(self.path).project_store
        self.assertEqual(restarted.listing()[0]['id'], self.pid)
        self.assertEqual(restarted.get(self.pid)['targets'], updated['targets'])
        self.assertEqual(updated['targets'][0]['sources'][-1]['previous']['description'], 'Manual assessment')
        self.assertEqual(restarted.get(self.other)['targets'], [])
        with self.assertRaises(LookupError):
            self.store.update_target(self.other, {'target_id': original['id'], 'name': 'Other', 'website': original['url']}, ACTOR)

    def test_search_metadata_rerun_exact_settings_and_preserves_manual(self):
        self.add(description='Manual assessment')
        first = self.search(num_results=5)
        run = first['searches'][0]
        self.assertEqual((run['status'], run['added'], run['duplicates'], run['omitted']), ('completed', 1, 1, 1))
        self.assertEqual(first['targets'][0]['description'], 'Manual assessment')
        self.assertEqual(len(first['targets'][0]['sources']), 2)
        self.search()  # Same operation cannot cause another paid call.
        self.adapter.search.assert_called_once()
        second = self.search('synthetic-two', rerun_id=run['id'], query='Must not replace saved query')
        self.assertEqual(second['searches'][-1]['parameters'], run['parameters'])
        self.assertEqual(second['searches'][-1]['added'], 0)
        self.assertEqual(len(second['targets']), 2)
        self.assertNotIn('raw_response', self.store.public(second)['searches'][0])
        self.assertIn('response_hash', run)
        with self.assertRaises(LookupError):
            self.store.run_search(self.other, {'operation_id': 'cross-project', 'rerun_id': run['id']}, ACTOR, self.adapter)

    def test_failed_disabled_invalid_and_concurrent_searches(self):
        self.adapter.search.side_effect = ExaError('synthetic sensitive provider failure')
        failed = self.search()
        self.assertEqual(failed['searches'][0]['status'], 'failed')
        self.assertNotIn('sensitive', json.dumps(failed))
        self.assertEqual(failed['targets'], [])
        self.adapter.enabled = False
        with self.assertRaises(ValueError):
            self.search('disabled')
        self.assertEqual(len(self.store.get(self.pid)['searches']), 1)
        self.adapter.enabled = True
        for count in (0, 101, True, '10'):
            with self.assertRaises(ValueError):
                self.search('invalid', num_results=count)
        def competing(params):
            with self.assertRaises(ValueError):
                self.search('competing')
            return {'results': []}
        self.adapter.search.side_effect = competing
        self.assertEqual(self.search('valid')['searches'][-1]['status'], 'completed')

    def test_clustering_evidence_snapshots_staleness_and_scoped_assets(self):
        self.search()
        self.add('unrelated.example.test', description='Retail apparel fashion clothing')
        result = self.store.run_clustering(self.pid, ACTOR)
        run = result['cluster_runs'][0]
        self.assertEqual(len(run['clusters']), 1)
        self.assertEqual(len(run['clusters'][0]['members']), 2)
        self.assertEqual(len(run['ungrouped']), 1)
        self.assertFalse(self.store.public(result)['cluster_runs'][0]['stale'])
        self.assertEqual(cluster(result['targets']), cluster(list(reversed(result['targets']))))
        self.assertEqual(run['input_hash'], input_hash(result['targets']))
        group = run['clusters'][0]
        body = {'kind': 'brief', 'title': 'Synthetic brief', 'body': 'Draft content', 'cluster_id': group['id'], 'cluster_run_id': run['id']}
        saved = self.store.add_asset(self.pid, body, ACTOR)
        self.assertEqual(saved['assets'][0]['status'], 'draft')
        with self.assertRaises(ValueError):
            self.store.add_asset(self.other, body, ACTOR)
        self.add('new.example.test', description='Additional energy evidence')
        stale = self.store.public(self.store.get(self.pid))
        self.assertTrue(stale['cluster_runs'][0]['stale'])
        self.assertEqual(stale['cluster_runs'][0]['clusters'], run['clusters'])

    def test_empty_evidence_is_not_clustered_and_urls_are_safe(self):
        self.add()
        self.add('other.example.test')
        run = self.store.run_clustering(self.pid, ACTOR)['cluster_runs'][0]
        self.assertEqual(run['clusters'], [])
        self.assertEqual(len(run['ungrouped']), 2)
        for url in ('javascript:alert(1)', 'https://user:pass@example.test', 'http://127.0.0.1',
                    'https://example.test:9000', 'example.test/\nattack', 'localhost', 'https://bad..test'):
            with self.subTest(url=url), self.assertRaises(ValueError):
                website(url)
        normalized, rejected = normalize_results({'results': [{'url': 'https://safe.example.test', 'entities': 12, 'highlights': None}, None]})
        self.assertEqual(len(normalized), 1)
        self.assertEqual(len(rejected), 1)

    def test_contacts_persist_deduplicate_and_keep_company_evidence_separate(self):
        self.search()
        company_run = self.store.run_clustering(self.pid, ACTOR)['cluster_runs'][0]
        body = {'name': 'Synthetic Person', 'company': 'Synthetic Grid', 'role': 'Research lead',
                'email': 'PERSON@EXAMPLE.TEST', 'profile_url': 'https://people.example.test/person/'}
        added = self.store.add_contact(self.pid, body, ACTOR)
        contact = added['contacts'][0]
        self.assertEqual(contact['email'], 'person@example.test')
        self.assertEqual(contact['profile_url'], 'https://people.example.test/person')
        self.assertEqual(len(added['targets']), 2)
        with self.assertRaises(ValueError):
            self.store.add_contact(self.pid, {**body, 'name': 'Duplicate identity'}, ACTOR)
        with self.assertRaises(ValueError):
            self.store.add_contact(self.pid, {**body, 'email': 'different@example.test'}, ACTOR)
        updated = self.store.update_contact(self.pid, {**body, 'contact_id': contact['id'], 'role': 'Updated role'}, ACTOR)
        self.assertEqual(updated['contacts'][0]['sources'][-1]['previous']['role'], 'Research lead')
        reloaded = Workspace(self.path).project_store
        self.assertEqual(reloaded.get(self.pid)['contacts'], updated['contacts'])
        self.assertEqual(reloaded.get(self.other)['contacts'], [])
        with self.assertRaises(LookupError):
            self.store.update_contact(self.other, {**body, 'contact_id': contact['id']}, ACTOR)
        self.assertEqual(reloaded.listing()[0]['target_count'], 3)
        self.assertEqual(reloaded.listing()[0]['contact_count'], 1)
        self.assertFalse(reloaded.public(updated)['cluster_runs'][0]['stale'])
        self.assertEqual(updated['cluster_runs'][0], company_run)

    def test_contacts_preserve_unknowns_validate_links_and_read_legacy_projects(self):
        with self.store.connect() as db:
            old = self.store.get(self.pid)
            old.pop('contacts')
            db.execute('UPDATE projects SET document = ? WHERE id = ?', (json.dumps(old), self.pid))
        self.assertEqual(self.store.get(self.pid)['contacts'], [])
        added = self.store.add_contact(self.pid, {'name': 'Synthetic Name Only'}, ACTOR)
        self.assertEqual(added['contacts'][0]['email'], '')
        self.assertEqual(added['contacts'][0]['review_status'], 'unreviewed')
        for invalid in ({'email': 'not-an-email'}, {'profile_url': 'javascript:alert(1)'}, {'name': ''}):
            with self.subTest(invalid=invalid), self.assertRaises(ValueError):
                self.store.add_contact(self.pid, {'name': 'Synthetic Invalid', **invalid}, ACTOR)

    def test_source_receipts_preserve_fields_and_independent_provenance(self):
        self.search()
        receipt = self.store.get(self.pid)['searches'][0]['contributions'][0]
        self.assertEqual(receipt['fields']['name'], 'Synthetic Grid')
        self.assertEqual(receipt['action'], 'added')
        upload_records = [{'record_type': 'company', 'name': 'Synthetic Grid from file',
                           'website': 'grid.example.test', 'description': 'File assessment'},
                          {'record_type': 'contact', 'name': 'Synthetic Person', 'email': 'person@example.test'}]
        self.store.import_source_records(self.pid, kind='upload', label='synthetic-targets.csv',
                                         records=upload_records, actor=ACTOR, operation_id='synthetic-upload')
        self.store.import_source_records(self.pid, kind='upload', label='synthetic-targets.csv',
                                         records=upload_records, actor=ACTOR, operation_id='synthetic-upload')
        project = self.store.import_source_records(self.pid, kind='mcp', label='Synthetic MCP server',
                                                   records=[{'record_type': 'contact', 'name': 'Synthetic Person',
                                                             'email': 'person@example.test', 'role': 'Source role'}],
                                                   actor=ACTOR, operation_id='synthetic-mcp')
        self.assertEqual(len(project['source_imports']), 2)
        self.assertEqual(len(project['contacts']), 1)
        self.assertEqual(len(project['targets']), 2)
        upload, mcp = project['source_imports']
        self.assertEqual(upload['contributions'][0]['action'], 'evidence_added')
        self.assertEqual(upload['contributions'][1]['action'], 'added')
        self.assertEqual(mcp['contributions'][0]['fields']['role'], 'Source role')
        self.assertEqual(project['targets'][0]['name'], 'Synthetic Grid')
        self.assertEqual(project['contacts'][0]['role'], '')
        self.assertEqual(project['contacts'][0]['sources'][-1]['import_id'], mcp['id'])
        self.assertEqual(mcp['actor'], ACTOR)
        self.assertIn('at', mcp)
        self.assertIn('input_hash', mcp)
        self.assertEqual(Workspace(self.path).project_store.get(self.pid)['source_imports'], project['source_imports'])
        self.assertEqual(self.store.get(self.other)['source_imports'], [])
        target = project['targets'][0]
        revised = self.store.update_target(self.pid, {'target_id': target['id'], 'name': 'Renamed manually',
                                                      'website': target['url']}, ACTOR)
        self.assertEqual(revised['searches'][0]['contributions'][0]['fields']['name'], 'Synthetic Grid')
        self.assertEqual(revised['source_imports'], project['source_imports'])

    def test_source_import_validation_is_atomic_and_does_not_invent_connections(self):
        with self.assertRaises(ValueError):
            self.store.import_source_records(self.pid, kind='upload', label='synthetic.csv', actor=ACTOR,
                                             operation_id='invalid-import', records=[
                                                 {'record_type': 'company', 'name': 'Synthetic', 'website': 'valid.example.test'},
                                                 {'record_type': 'contact', 'name': 'Synthetic', 'email': 'invalid'}])
        project = self.store.get(self.pid)
        self.assertEqual(project['targets'], [])
        self.assertEqual(project['source_imports'], [])
        self.assertNotIn('mcp_connected', project)
        self.adapter.search.return_value = {'results': []}
        project = self.search()
        self.assertEqual(project['searches'][0]['contributions'], [])

    def test_source_status_follows_live_records_removal_and_restoration(self):
        project = self.search()
        searches = project['searches']
        ids = [record['id'] for record in project['targets']]
        self.assertTrue(self.store.public(project)['source_usage']['searches'])
        project = self.store.remove_record(self.pid, {'record_type': 'company', 'record_id': ids[0]}, ACTOR)
        self.assertEqual(self.store.public(project)['source_record_counts']['searches'], 1)
        project = self.store.remove_record(self.pid, {'record_type': 'company', 'record_id': ids[1]}, ACTOR)
        self.assertFalse(self.store.public(project)['source_usage']['searches'])
        self.assertEqual(project['searches'], searches)
        self.assertEqual(len(project['removed_records']), 2)
        restored = self.store.restore_record(self.pid, {'removed_id': project['removed_records'][0]['id']}, ACTOR)
        self.assertTrue(self.store.public(restored)['source_usage']['searches'])
        self.assertEqual(restored['targets'][0]['id'], ids[0])
        self.assertEqual(restored['searches'], searches)
        self.assertEqual(Workspace(self.path).project_store.public(restored)['source_record_counts']['searches'], 1)
        for kind in ('upload', 'mcp'):
            project = self.store.import_source_records(self.pid, kind=kind, label='Synthetic ' + kind,
                records=[{'record_type': 'contact', 'name': 'Synthetic Person', 'email': 'synthetic@example.test'}],
                actor=ACTOR, operation_id='synthetic-' + kind)
        self.assertEqual(self.store.public(project)['source_usage'], {'searches': True, 'upload': True, 'mcp': True})
        imports = project['source_imports']
        project = self.store.remove_record(self.pid, {'record_type': 'contact', 'record_id': project['contacts'][0]['id']}, ACTOR)
        self.assertEqual(self.store.public(project)['source_usage'], {'searches': True, 'upload': False, 'mcp': False})
        self.assertEqual(project['source_imports'], imports)
        removed_id = next(entry['id'] for entry in project['removed_records'] if entry['record_type'] == 'contact')
        project = self.store.restore_record(self.pid, {'removed_id': removed_id}, ACTOR)
        self.assertEqual(self.store.public(project)['source_usage'], {'searches': True, 'upload': True, 'mcp': True})

    def test_removal_scope_and_restore_identity_conflicts(self):
        project = self.add()
        record_id = project['targets'][0]['id']
        with self.assertRaises(LookupError):
            self.store.remove_record(self.other, {'record_type': 'company', 'record_id': record_id}, ACTOR)
        project = self.store.remove_record(self.pid, {'record_type': 'company', 'record_id': record_id}, ACTOR)
        removed_id = project['removed_records'][0]['id']
        with self.assertRaises(LookupError):
            self.store.restore_record(self.other, {'removed_id': removed_id}, ACTOR)
        self.add()
        with self.assertRaises(ValueError):
            self.store.restore_record(self.pid, {'removed_id': removed_id}, ACTOR)
        self.assertEqual(len(self.store.get(self.pid)['removed_records']), 1)
        self.assertEqual(self.store.public(self.store.get(self.pid))['source_usage'], {'searches': False, 'upload': False, 'mcp': False})

    def test_http_client_can_edit_search_and_read_only_own_projects(self):
        server = PortalServer(self.path, 0)
        server.exa = self.adapter
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        access = server.workspace.access
        admin = access.principal(access.local_session())
        access.change_domain(admin, 'add', 'client.example')
        token = access.google_session({'email': 'person@client.example', 'subject': 'synthetic-client', 'domain': 'client.example'})
        def request(method, path, body=None, authenticated=True, origin=True):
            conn = http.client.HTTPConnection('127.0.0.1', server.server_port)
            headers = {'Content-Type': 'application/json'}
            if authenticated:
                headers['Cookie'] = 'portal_session=' + token
            if origin:
                headers['Origin'] = server.origin
            conn.request(method, path, json.dumps(body) if body is not None else None, headers)
            response = conn.getresponse()
            status, value = response.status, json.loads(response.read())
            conn.close()
            return status, value
        try:
            route = '/api/project?id=' + self.pid
            self.assertEqual(request('GET', route, authenticated=False)[0], 401)
            self.assertEqual(request('GET', route)[0], 200)
            self.assertEqual(request('GET', route+'&client=')[0], 400)
            self.assertEqual(request('GET', '/api/project?id=foreign')[0], 404)
            body = {'project_id': self.pid, 'name': 'Synthetic Client Entry', 'website': 'cliententry.example.test'}
            self.assertEqual(request('POST', '/api/project/target/add', body, origin=False)[0], 403)
            status, payload = request('POST', '/api/project/target/add', body)
            self.assertEqual(status, 200, payload)
            self.assertEqual(payload['project']['targets'][0]['sources'][0]['actor'], 'person@client.example')
            contact_body = {'project_id': self.pid, 'name': 'Synthetic Client Contact', 'email': 'synthetic@example.test'}
            self.assertEqual(request('POST', '/api/project/contact/add', contact_body, authenticated=False)[0], 401)
            self.assertEqual(request('POST', '/api/project/contact/add', contact_body, origin=False)[0], 403)
            status, payload = request('POST', '/api/project/contact/add', contact_body)
            self.assertEqual(status, 200, payload)
            contact = payload['project']['contacts'][0]
            self.assertEqual(contact['sources'][0]['actor'], 'person@client.example')
            status, payload = request('POST', '/api/project/contact/update', {**contact_body, 'contact_id': contact['id'], 'role': 'Synthetic role'})
            self.assertEqual(status, 200, payload)
            self.assertEqual(payload['project']['contacts'][0]['role'], 'Synthetic role')
            removal = {'project_id': self.pid, 'record_type': 'contact', 'record_id': contact['id']}
            self.assertEqual(request('POST', '/api/project/record/remove', removal, authenticated=False)[0], 401)
            self.assertEqual(request('POST', '/api/project/record/remove', removal, origin=False)[0], 403)
            status, payload = request('POST', '/api/project/record/remove', removal)
            self.assertEqual(status, 200, payload)
            self.assertEqual(payload['project']['contacts'], [])
            removed_id = payload['project']['removed_records'][0]['id']
            status, payload = request('POST', '/api/project/record/restore', {'project_id': self.pid, 'removed_id': removed_id})
            self.assertEqual(status, 200, payload)
            self.assertEqual(payload['project']['contacts'][0]['id'], contact['id'])

            status, payload = request('POST', '/api/project/search', {'project_id': self.pid, 'operation_id': 'http-search', 'query': 'Synthetic companies'})
            self.assertEqual(status, 200, payload)
            self.assertEqual(payload['project']['searches'][0]['status'], 'completed')
            self.assertEqual(request('POST', '/api/admin/domains', {'action': 'add', 'domain': 'other.example'})[0], 403)
            access.change_domain(admin, 'remove', 'client.example')
            self.assertEqual(request('GET', route)[0], 401)
        finally:
            server.shutdown()
            server.server_close()
            thread.join()


class ExaTransportTests(unittest.TestCase):
    @patch.dict('os.environ', {'EXA_API_KEY': 'synthetic-key'}, clear=True)
    @patch('gtm_pipeline.adapters.exa_search.build_opener')
    def test_fixed_endpoint_bounded_read_and_no_redirect_handler(self, builder):
        response = Mock()
        response.read.return_value = b'{"results": []}'
        builder.return_value.open.return_value.__enter__.return_value = response
        adapter = ExaSearch()
        self.assertEqual(adapter.search({'query': 'Synthetic only'})['results'], [])
        request = builder.return_value.open.call_args.args[0]
        self.assertEqual(request.full_url, 'https://api.exa.ai/search')
        self.assertEqual(request.get_header('X-api-key'), 'synthetic-key')
        response.read.assert_called_once_with(8_000_001)
        self.assertEqual(builder.return_value.open.call_count, 1)
        self.assertIsNone(builder.call_args.args[0].redirect_request(None, None, 302, '', {}, 'https://other.example'))

    @patch.dict('os.environ', {'EXA_API_KEY': 'synthetic-key'}, clear=True)
    @patch('gtm_pipeline.adapters.exa_search.build_opener')
    def test_provider_errors_sanitized_without_retry(self, builder):
        builder.return_value.open.side_effect = HTTPError('https://api.exa.ai/search', 401, 'synthetic-secret', {}, io.BytesIO(b'secret'))
        with self.assertRaisesRegex(ExaError, 'rejected the API key') as raised:
            ExaSearch().search({'query': 'Synthetic only'})
        self.assertNotIn('synthetic-secret', str(raised.exception))
        builder.return_value.open.assert_called_once()
