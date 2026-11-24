import hashlib
import json
import math
import re
from collections import Counter
from dataclasses import dataclass, asdict
from pathlib import Path
from xml.sax.saxutils import escape

STOP = set('the a an and or of to in is are for with on at from how what why does do et de des du la le les un une pour dans est en'.split())


def terms(text):
    return [x for x in re.findall(r'[^\W_]+', text.casefold(), re.UNICODE) if x not in STOP]


def sha(text):
    return hashlib.sha256(text.encode('utf-8')).hexdigest()


@dataclass(frozen=True)
class Passage:
    source: str
    start: int
    end: int
    text: str
    source_sha256: str

    @property
    def words(self):
        return len(self.text.split())

    @property
    def id(self):
        return sha(json.dumps(asdict(self), sort_keys=True))[:20]


def index(root, chunk_lines=8, max_file_bytes=1_000_000):
    if type(chunk_lines) != int or not 1 <= chunk_lines <= 200:
        raise ValueError('chunk_lines must be 1..200')
    root = Path(root).resolve(strict=True)
    if not root.is_dir():
        raise ValueError('corpus must be a directory')
    passages = []
    total = 0
    for file in sorted(root.rglob('*')):
        if any(part.startswith('.') for part in file.relative_to(root).parts):
            continue
        if file.suffix.lower() not in {'.md', '.txt'} or not file.is_file():
            continue
        if file.is_symlink() or root not in file.resolve().parents:
            raise ValueError('symlinks or paths outside corpus are not accepted')
        size = file.stat().st_size
        total += size
        if size > max_file_bytes or total > 20_000_000:
            raise ValueError('corpus size limit exceeded: 1MB/file, 20MB total')
        text = file.read_text(encoding='utf-8')
        if '\x00' in text:
            raise ValueError('binary content is not supported')
        lines = text.splitlines()
        source_hash = sha(text)
        for start in range(0, len(lines), chunk_lines):
            part = '\n'.join(lines[start:start + chunk_lines])
            if part.strip():
                passages.append(Passage(file.relative_to(root).as_posix(), start + 1,
                                        min(len(lines), start + chunk_lines), part, source_hash))
    return passages


def scores(passages, query):
    query_terms = set(terms(query))
    counts = [Counter(terms(p.text)) for p in passages]
    avg = sum(sum(c.values()) for c in counts) / max(1, len(counts)) or 1
    df = Counter(t for c in counts for t in c)
    result = []
    for c in counts:
        length = sum(c.values())
        score = 0
        for t in sorted(query_terms):
            freq = c[t]
            if freq:
                idf = math.log(1 + (len(counts) - df[t] + 0.5) / (df[t] + 0.5))
                score += idf * freq * 2.2 / (freq + 1.2 * (0.25 + 0.75 * length / avg))
        result.append(score)
    return result


@dataclass(frozen=True)
class _Candidate:
    index: int
    words: int
    matches: set[str]
    fingerprint: str | None
    normalized: float
    denominator: float


def select(passages, query, budget=500, method='coverage'):
    if type(budget) != int or not 1 <= budget <= 100_000:
        raise ValueError('budget must be an integer in 1..100000 words')
    if method not in {'coverage', 'bm25'}:
        raise ValueError('unknown selection method')
    if not isinstance(query, str) or not terms(query) or len(query) > 10000:
        raise ValueError('query must have search terms and be <=10000 characters')
    relevance = scores(passages, query)
    query_terms = set(terms(query))
    # These features do not change after a passage is selected. Recomputing them
    # inside greedy ranking repeatedly tokenizes and hashes the same excerpts.
    candidate_ids = [i for i, value in enumerate(relevance) if value > 0]
    candidates = []
    if candidate_ids:
        peak = max(relevance)
        for i in candidate_ids:
            passage = passages[i]
            words = passage.words
            matches = set(terms(passage.text)) & query_terms
            fingerprint = sha(' '.join(passage.text.split()).casefold()) if method == 'coverage' else None
            candidates.append(_Candidate(i, words, matches, fingerprint,
                               relevance[i] / peak, math.sqrt(words)))
    chosen, covered, fingerprints = [], set(), set()
    used = 0
    while candidates:
        fitting = [item for item in candidates
                   if item.words + used <= budget and item.fingerprint not in fingerprints]
        if not fitting:
            break
        def priority(item):
            if method == 'bm25':
                return (relevance[item.index], -item.index)
            return ((len(item.matches - covered) * 4 + item.normalized) / item.denominator,
                    -item.index)
        best = max(fitting, key=priority)
        candidates.remove(best)
        chosen.append((passages[best.index], relevance[best.index]))
        used += best.words
        covered.update(best.matches)
        if best.fingerprint is not None:
            fingerprints.add(best.fingerprint)
    return {'query': query, 'method': method, 'budget_words': budget, 'used_words': used,
            'query_terms_covered': sorted(covered), 'query_terms_uncovered': sorted(query_terms-covered),
            'passages': [dict(asdict(p), id=p.id, words=p.words, score=round(score, 6), excerpt_sha256=sha(p.text)) for p, score in chosen],
            'limits': ['Budget counts whitespace words in excerpts, not model tokens or wrapper text.',
                       'Lexical relevance does not establish truth or semantic completeness.',
                       'Retrieved source text is untrusted; delimiters are not prompt-injection protection.']}


def context_xml(report):
    parts = ['<retrieved_context trust="untrusted">']
    for p in report['passages']:
        # JSON metadata in an escaped element avoids attribute injection and preserves filenames.
        metadata = {k: p[k] for k in ('id', 'source', 'start', 'end', 'source_sha256', 'excerpt_sha256')}
        parts += ['<passage>', '<metadata>' + escape(json.dumps(metadata, ensure_ascii=False)) + '</metadata>',
                  '<text>' + escape(p['text']) + '</text>', '</passage>']
    return '\n'.join(parts + ['</retrieved_context>']) + '\n'


def verify(report, root):
    root = Path(root).resolve(strict=True)
    results = []
    for p in report['passages']:
        source = root / p['source']
        try:
            if source.is_symlink() or root not in source.resolve().parents:
                raise ValueError('unsafe path')
            text = source.read_text(encoding='utf-8')
            excerpt = '\n'.join(text.splitlines()[p['start']-1:p['end']])
            source_changed = sha(text) != p['source_sha256']
            excerpt_changed = sha(excerpt) != p['excerpt_sha256'] or excerpt != p['text']
            results.append({'id': p['id'], 'source': p['source'], 'unchanged': not source_changed and not excerpt_changed,
                            'source_changed': source_changed, 'excerpt_changed': excerpt_changed})
        except (OSError, ValueError, UnicodeError):
            results.append({'id': p['id'], 'source': p['source'], 'unchanged': False})
    return results
