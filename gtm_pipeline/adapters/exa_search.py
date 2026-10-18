"""Bounded Exa company search. Explicit calls only; no automatic paid retries."""

import json
import os
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import HTTPRedirectHandler, Request, build_opener
from urllib.parse import urlsplit


class ExaError(ValueError):
    pass


class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


class ExaSearch:
    def __init__(self, key_file=None):
        self.key = os.environ.get('EXA_API_KEY', '').strip()
        if key_file and Path(key_file).exists():
            self.key = Path(key_file).read_text().strip()
        self.enabled = bool(self.key)

    def search(self, parameters):
        if not self.enabled:
            raise ExaError('Exa is not configured. Ask your operator to connect the API key.')
        request = Request('https://api.exa.ai/search', data=json.dumps(parameters).encode(), method='POST',
                          headers={'x-api-key': self.key, 'Content-Type': 'application/json'})
        try:
            with build_opener(NoRedirect()).open(request, timeout=45) as response:
                raw = response.read(8_000_001)
            if len(raw) > 8_000_000:
                raise ExaError('Exa returned an oversized response. Review provider usage before retrying.')
            result = json.loads(raw)
            if not isinstance(result, dict) or not isinstance(result.get('results'), list):
                raise ExaError('Exa returned an invalid response. Review provider usage before retrying.')
            json.dumps(result, allow_nan=False)
            return result
        except HTTPError as error:
            messages = {401: 'Exa rejected the API key.', 402: 'Exa requires available credits.',
                        429: 'Exa rate limit reached. Try again later.'}
            raise ExaError(messages.get(error.code, 'Exa search failed. Review provider usage before retrying.')) from None
        except (URLError, TimeoutError, OSError, ValueError) as error:
            if isinstance(error, ExaError):
                raise
            raise ExaError('Exa did not return a usable response. Usage may have occurred; no automatic retry was made.') from None


def normalize_results(response):
    """Preserve result evidence without claiming company qualification."""
    targets, rejected = [], []
    aggregators = {'linkedin.com', 'crunchbase.com', 'pitchbook.com', 'tracxn.com', 'wellfound.com'}
    for result in response['results']:
        if not isinstance(result, dict):
            rejected.append('Malformed result')
            continue
        url = result.get('url', '')
        try:
            host = urlsplit(url).hostname or ''
            host = host.removeprefix('www.').lower()
            if host in aggregators or any(host.endswith('.' + domain) for domain in aggregators):
                rejected.append('Directory/profile result requires company website review')
                continue
        except (TypeError, ValueError):
            rejected.append('Invalid source URL')
            continue
        highlights = result.get('highlights', [])
        if not isinstance(highlights, list):
            highlights = []
        text = result.get('text') or result.get('summary') or '\n'.join(h for h in highlights if isinstance(h, str))
        name, description = result.get('title') or host, text or ''
        entities = result.get('entities')
        for entity in entities if isinstance(entities, list) else []:
            if isinstance(entity, dict) and entity.get('type') == 'company':
                properties = entity.get('properties')
                if not isinstance(properties, dict):
                    continue
                name = properties.get('name') or name
                description = properties.get('description') or description
                break
        targets.append({'name': str(name)[:200], 'website': url, 'description': str(description)[:6000],
                        'sector': '', 'tags': [], 'notes': '',
                        'source_excerpt': str(text or description)[:6000]})
    return targets, rejected
