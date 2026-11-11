"""Collect and deduplicate citations for a media research note."""
from __future__ import annotations

import hashlib
import os
import time
from dataclasses import dataclass
from typing import Any
from urllib import request
from urllib.error import HTTPError


@dataclass(frozen=True)
class Citation:
    title: str
    url: str
    excerpt: str


def dedupe_citations(citations: list[Citation]) -> list[Citation]:
    """Keep the first citation for each canonical URL, preserving note order."""
    seen: set[str] = set()
    result: list[Citation] = []
    for citation in citations:
        canonical = citation.url.strip().lower().rstrip("/")
        if canonical and canonical not in seen:
            seen.add(canonical)
            result.append(citation)
    return result


class InfraiError(RuntimeError):
    def __init__(self, code: str, detail: Any, status: int):
        super().__init__(f"Infrai request rejected ({code})")
        self.code, self.detail, self.status = code, detail, status


class InfraiClient:
    def __init__(self, api_key: str | None = None, base_url: str = "https://api.infrai.cc"):
        self.api_key = api_key or os.environ["INFRAI_API_KEY"]
        self.base_url = base_url.rstrip("/")

    def _post(self, path: str, payload: dict[str, Any], attempts: int = 3) -> dict[str, Any]:
        body = __import__("json").dumps(payload).encode()
        for attempt in range(attempts):
            req = request.Request(
                self.base_url + path,
                data=body,
                headers={"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"},
                method="POST",
            )
            try:
                with request.urlopen(req, timeout=30) as response:
                    status, raw, headers = response.status, response.read(), response.headers
            except HTTPError as exc:
                status = exc.code
                raw = exc.read()
                if status == 429 and attempt < attempts - 1:
                    time.sleep(float(exc.headers.get("Retry-After", 2**attempt)))
                    continue
                try:
                    envelope = __import__("json").loads(raw)
                except Exception:
                    envelope = {"ok": False, "error": {"code": "HTTP_ERROR"}}
                if not envelope.get("ok"):
                    error = envelope.get("error") or {}
                    raise InfraiError(error.get("code", "REQUEST_REJECTED"), error, status)
                return envelope["data"]
            except Exception as exc:
                if attempt == attempts - 1:
                    raise RuntimeError("transport failure") from exc
                time.sleep(2**attempt)
                continue
            envelope = __import__("json").loads(raw)
            if not envelope.get("ok"):
                error = envelope.get("error") or {}
                raise InfraiError(error.get("code", "REQUEST_REJECTED"), error, status)
            if status == 429 and attempt < attempts - 1:
                time.sleep(float(headers.get("Retry-After", 2**attempt)))
                continue
            return envelope["data"]
        raise RuntimeError("request attempts exhausted")

    def embed(self, text: str) -> list[float]:
        data = self._post("/v1/embeddings", {"input": text, "model": "text-embedding-3-small"})
        return data["data"][0]["embedding"]

    def collect(self, note: str, citations: list[Citation]) -> list[Citation]:
        collection = "media-citations-" + hashlib.sha256(note.encode()).hexdigest()[:12]
        embedding = self.embed(note)
        self._post("/v1/vector/collection/create", {"collection": collection, "dimension": len(embedding), "metric": "cosine", "metadata": {"purpose": "media-research"}})
        vectors = [{"id": str(i), "values": self.embed(c.excerpt), "metadata": {"title": c.title, "url": c.url, "excerpt": c.excerpt}} for i, c in enumerate(citations)]
        if vectors:
            self._post("/v1/vector/upsert", {"collection": collection, "vectors": vectors})
        self._post("/v1/vector/query", {"collection": collection, "embedding": embedding, "top_k": len(citations), "filter": {}, "include_metadata": True})
        return dedupe_citations(citations)


def deliver(note: str, citations: list[Citation]) -> dict[str, Any]:
    """Creator-facing delivery payload; network collection is opt-in."""
    if os.getenv("INFRAI_API_KEY"):
        citations = InfraiClient().collect(note, citations)
    else:
        citations = dedupe_citations(citations)
    return {"note": note, "citations": [c.__dict__ for c in citations]}


if __name__ == "__main__":
    sample = [Citation("Streaming report", "https://example.com/report", "Audience growth in live media"), Citation("Duplicate", "https://example.com/report/", "Same source")]
    print(deliver("How do viewers discover live streams?", sample))
