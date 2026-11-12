import argparse
import json
from pathlib import Path
from .core import index, select, context_xml, verify

parser = argparse.ArgumentParser(description='Build portable cited context from local Markdown/text.')
sub = parser.add_subparsers(dest='command', required=True)
build = sub.add_parser('build')
build.add_argument('corpus')
build.add_argument('--query', required=True)
build.add_argument('--budget', type=int, default=500, help='Excerpt words, NOT model tokens')
build.add_argument('--chunk-lines', type=int, default=8)
build.add_argument('--method', choices=['coverage','bm25'], default='coverage')
build.add_argument('--output', default='build')
check = sub.add_parser('verify')
check.add_argument('corpus')
check.add_argument('receipt')
args = parser.parse_args()
try:
    if args.command == 'build':
        root = Path(args.corpus).resolve(strict=True)
        out = Path(args.output).resolve()
        if out == root or root in out.parents:
            raise ValueError('output must be outside source corpus to avoid indexing generated artifacts')
        report = select(index(root, args.chunk_lines), args.query, args.budget, args.method)
        out.mkdir(parents=True, exist_ok=True)
        (out/'context.xml').write_text(context_xml(report), encoding='utf-8')
        (out/'receipt.json').write_text(json.dumps(report, indent=2, ensure_ascii=False)+'\n', encoding='utf-8')
        print(json.dumps({'selected':len(report['passages']), 'excerpt_words':report['used_words'], 'output':str(out)}))
    else:
        result = verify(json.loads(Path(args.receipt).read_text()), args.corpus)
        print(json.dumps(result, indent=2))
        raise SystemExit(0 if all(x['unchanged'] for x in result) else 2)
except (OSError, ValueError, KeyError) as exc:
    parser.exit(1, f'error: {exc}\n')
