"""Deterministic, explainable text-similarity groups over supplied target evidence."""

from collections import Counter
import hashlib
import json
import math
import re

STOP = frozenset('the and for with that this from are was were have has our your their they them its into company companies business businesses solutions solution services service leading global more about also through provide provides provider platform using based'.split())


def inputs(targets):
    return [{'id': target['id'], 'domain': target['domain'], 'name': target['name'],
             **{field: target.get(field, '') for field in ('description', 'sector', 'notes')},
             'tags': target.get('tags', []), 'sources': target.get('sources', [])}
            for target in sorted(targets, key=lambda target: target['id'])]


def input_hash(targets):
    return hashlib.sha256(json.dumps(inputs(targets), sort_keys=True, allow_nan=False).encode()).hexdigest()


def cluster(targets, threshold=0.24):
    """Connected components of cosine-similarity edges, not calibrated ICP fit."""
    records = inputs(targets)
    counters = []
    for target in records:
        text = ' '.join([target['description'], target['notes'], target['sector'], target['sector'],
                         ' '.join(target['tags']), ' '.join(target['tags'])])
        counters.append(Counter(word for word in re.findall(r'[a-z][a-z0-9-]{2,}', text.lower()) if word not in STOP))
    df = Counter(word for words in counters for word in words)
    vectors = []
    for words in counters:
        vector = {word: (1 + math.log(count)) * (math.log((len(records) + 1) / (df[word] + 1)) + 1)
                  for word, count in words.items()}
        norm = math.sqrt(sum(value * value for value in vector.values()))
        vectors.append({word: value / norm for word, value in vector.items()} if norm else {})
    parents = list(range(len(records)))
    def root(index):
        while parents[index] != index:
            parents[index] = parents[parents[index]]
            index = parents[index]
        return index
    edges = []
    for left in range(len(records)):
        for right in range(left + 1, len(records)):
            shared = vectors[left].keys() & vectors[right].keys()
            similarity = sum(vectors[left][word] * vectors[right][word] for word in shared)
            if similarity >= threshold and shared:
                parents[root(right)] = root(left)
                edges.append({'left': records[left]['id'], 'right': records[right]['id'],
                              'similarity': round(similarity, 4), 'shared_terms': sorted(shared)[:12]})
    components = {}
    for index in range(len(records)):
        components.setdefault(root(index), []).append(index)
    groups, ungrouped = [], []
    for indexes in components.values():
        if len(indexes) < 2:
            ungrouped.extend(records[index]['id'] for index in indexes)
            continue
        members = [records[index] for index in indexes]
        ids = sorted(member['id'] for member in members)
        frequencies = Counter(word for index in indexes for word in counters[index])
        terms = sorted((word for word, n in frequencies.items() if n > 1),
                       key=lambda word: (-frequencies[word], word))[:6]
        groups.append({'id': hashlib.sha256('|'.join(ids).encode()).hexdigest()[:16],
                       'label': ' · '.join(terms[:3]).title(), 'shared_terms': terms,
                       'members': members, 'relationships': [edge for edge in edges if edge['left'] in ids and edge['right'] in ids]})
    return {'method': 'tfidf-cosine-components-v1', 'threshold': threshold,
            'input_hash': input_hash(targets), 'clusters': groups, 'ungrouped': ungrouped,
            'note': 'Draft groups from supplied descriptions, sector, tags and notes. Targets are connected by shared text signals; not every pair is similar. Missing evidence remains ungrouped. Similarity is not buying intent.'}
