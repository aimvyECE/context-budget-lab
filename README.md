# Context Budget Lab

**Take your evidence with you, not just your chat history.**

A local, dependency-free Python prototype that turns a folder of Markdown/text into a compact, cited context bundle for any assistant. It is a **context compiler, not a language model or chatbot**. No API key, account, embeddings, network requests or paid inference are needed.

## The useful difference

Instead of pasting a whole folder into one assistant, select exact passages under an excerpt-word budget, export a provider-neutral XML bundle, and retain line references plus hashes. When source material changes, verify which evidence is stale before reusing it.

This offers portable, inspectable retrieval and a reproducible change-detection workflow. It does **not** claim better answers than Claude, ChatGPT, or any other model. No comparison against those services has been run.

## Try it in 30 seconds

Python 3.10+, standard library only. From this repository:

```sh
python -m context_budget build examples/corpus \
  --query 'battery capacity electricity tariff' --budget 100 --output build/demo
python -m context_budget verify examples/corpus build/demo/receipt.json
python -m unittest discover -s tests -v
PYTHONPATH=. python examples/benchmark.py
```

Open `build/demo/context.xml` and `receipt.json`. The XML can be pasted into your preferred assistant as **untrusted reference material**, alongside your question. Check its final answer against the original sources. Neither export nor verification contacts an external service.

Change a tariff in a *copy* of the example corpus, then run `verify` again: the exit status becomes 2 and the affected passage is marked stale. The report distinguishes a whole-source change from a change to the cited excerpt. It does not silently rewrite your original context or answer.

## What it implements

- Local `.md` / `.txt` reading, fixed line chunks and deterministic ordering.
- BM25 lexical ranking baseline, compared with an explicit word-budget/diversity heuristic.
- Exact normalized-duplicate suppression in the coverage strategy.
- Exact excerpts, relative filenames, line ranges, excerpt and whole-source SHA256.
- Escaped XML suitable for transport, with JSON metadata and a receipt.
- Source-change verification, including edits outside the cited lines.
- Explicit no-match results, bounded file sizes and refusal of symlink inputs.

`--budget` counts whitespace **words in excerpts only**, not tokenizer tokens, wrapper overhead, or the eventual prompt. `--chunk-lines` controls passage size; oversized chunks are skipped, not silently truncated. `--method bm25` selects the transparent baseline.

## A small, honest benchmark

The included four **constructed regression fixtures** are designed to expose behavior, not establish real-world superiority. Run the script to reproduce:

| Scenario | BM25 gold-source recall | Coverage gold-source recall |
| --- | ---: | ---: |
| Repeated keyword-heavy copies displace two useful documents | 0/2 | 2/2 |
| Simple focused query | 1/1 | 1/1 |
| Synonym-only query, no lexical overlap | 0/1 | 0/1 |
| Budget smaller than the only relevant passage | 0/1 | 0/1 |

The first improvement mostly demonstrates duplicate suppression. It is **not** evidence that this heuristic beats a production retriever. Gold-source recall is not factual answer correctness. No LLM inference was used. Full scenarios and outputs: [`examples/benchmark.py`](examples/benchmark.py), [`docs/benchmark.json`](docs/benchmark.json).

## Privacy and trust boundaries

Use a deliberately curated corpus. Hidden files/directories are ignored; no secret detector is implemented. Ordinary filenames and document text can still contain private information. Outputs contain copies of those excerpts: **review before uploading, sharing or committing them**. Output must be outside the corpus; generated build files are gitignored.

The tool does not execute source instructions. XML escaping preserves boundaries but **does not make an LLM immune to prompt injection**. Treat retrieved text as untrusted. Hashes detect changes against a receipt you already trust; receipts are **not signed or authenticated** and are not proof of authorship, truth or tamper resistance against an attacker who can rewrite both files and receipt.

## Limits and next experiments

- Lexical matching cannot resolve paraphrases, contradictions, chronology or intent. The synthetic old/new tariff example intentionally exposes this limitation.
- No answer generation, embedding search, semantic reranker, chat UI, persistence service or model integration yet.
- Fixed line chunks are basic; no PDF, Office, images, OCR, binary or nested repository ingestion.
- Prototype for small corpora, capped at 1 MB per file and 20 MB total. Index rebuilt per call; not stress-tested at the cap.
- Greedy coverage heuristic, not an optimal knapsack solver; it can prefer short shallow passages.
- No deduced token/cost savings claim: use the target model's tokenizer and current pricing for that.

Promising next work: local optional embeddings with a licensed model; sentence-aware chunks; a frozen held-out retrieval set with human relevance labels; exact tokenizer adapters; incremental dependency graphs for answers; optional local-model generation clearly separated from extraction. Those are **roadmap items, not implemented features**.

## Attribution and engineering status

AI-assisted prototype developed for Mahé Vidot. All included source documents are synthetic; no private notes or account information are included. BM25 and diversity-aware retrieval are established ideas, not claimed inventions. This is an original compact implementation, not a fork or copied engine. See [design and sources](docs/DESIGN.md). Code licensed MIT; external research retains its own terms.
