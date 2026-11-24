# Design / related work

## Algorithm

Unicode alphanumeric case-folded terms with a small explicit English/French stop-word list; BM25 k1=1.2, b=0.75. Terms are not stemmed. Corpus order is stable. A candidate is relevant only if it shares at least one query term.

Baseline takes the highest BM25-scoring remaining passage that fits. Coverage mode uses `(4 * newly covered query terms + normalized BM25) / sqrt(excerpt words)`, suppresses exact whitespace-normalized case-folded duplicates, and fits greedily. The coefficient 4 is a transparent heuristic, not a trained parameter. It was not tuned or validated on a representative dataset. Query coverage is merely lexical coverage, never a completeness certificate.

Ranking caches static passage features and calculates the whole-source hash once per
file. Coverage still rescans the remaining candidates as terms are covered, so this
is not a guarantee of linear runtime or a large-corpus benchmark.

Metadata retains source hashes and exact line references. Verification checks the complete source and the cited excerpt separately. Edits shifting line positions may invalidate an otherwise identical excerpt: relocation is deliberately not guessed.

## Prior art

- Robertson & Zaragoza, *The Probabilistic Relevance Framework: BM25 and Beyond* (2009), https://doi.org/10.1561/1500000019
- Carbonell & Goldstein, *The Use of MMR, Diversity-Based Reranking for Reordering Documents and Producing Summaries* (1998), https://doi.org/10.1145/290941.291025 . Inspiration for diversity motivation only: this project's coverage heuristic is **not MMR**.
- BEIR benchmark: https://github.com/beir-cellar/beir . Future evaluation candidate; no BEIR results are claimed here and no BEIR code/data is bundled.

No external implementation is copied and there are no runtime dependencies. MIT licensing applies to this repository's original code, not to any future external model or dataset. Inspect those licenses independently.
