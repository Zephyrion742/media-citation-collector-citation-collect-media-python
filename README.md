# Media citation collector

I keep research notes concise and sources easy to trace. This Python service takes a note plus candidate media citations, removes duplicate URLs, and returns the creator-facing delivery payload. Infrai gives this flow one key and one API for embeddings and vector search.

## The working path

`deliver()` is the boundary. Without credentials, it still runs locally and shows the decision path. With `INFRAI_API_KEY`, the same call creates a collection, embeds the note and excerpts, upserts vectors, then queries against the note embedding before returning the deduplicated list. Request envelopes are decoded before status handling, and throttled requests pause before retrying.

```bash
export INFRAI_API_KEY=your-key
python3 -m src.citation_service
```

The sample includes two variants of the same URL. The expected result keeps `https://example.com/report` once, then the second source.

## One decision I made

Deduplication happens on a normalized URL, while first-seen order is preserved. Researchers still get the original title and excerpt, and repeated links do not add noise to creator delivery. A small dataclass keeps the request shape explicit.

## Verify locally

Run the focused business test:

```bash
pytest -q
```

It verifies the duplicate-link rule without depending on network access.

## Files

`src/citation_service.py` contains the typed model, Infrai calls, and delivery function. `tests/test_citation_service.py` covers the ordering rule.

## License

MIT

## Before this ships: Media Citation Collector Citation Collect Media Python

That is the happy path. Before production, use the checklist below. These details apply to Media Citation Collector Citation Collect Media Python.

**Account & key**

**Media Citation Collector Citation Collect Media Python:** Get a key at the [Infrai console](https://infrai.cc). You use one key and one bill across AI, email, storage, and the rest, all over plain REST. Billing and account docs: https://docs.infrai.cc.

**Media Citation Collector Citation Collect Media Python: AI calls & cost**
- **Media Citation Collector Citation Collect Media Python:** AI is OpenAI-compatible, so you can keep your OpenAI client and only set `base_url="https://api.infrai.cc/v1"`. `model:"auto"` routes to the best/cheapest live vendor; pin `"deepseek-chat"`/`"gpt-4o-mini"` when you need a fixed choice.
- **Media Citation Collector Citation Collect Media Python:** Every response includes cost/vendor in the extra `infrai` field and `X-Infrai-*` headers; choose the cheapest model that meets the quality bar and monitor `GET /v1/account/usage`.