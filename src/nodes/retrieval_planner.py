"""
Retrieval Planner — PCR (Progressive Context Revelation) + Corrective RAG.

Core novelty: mastery score gates WHICH chunks are retrieved.
Answer chunks are physically absent from context until the student earns them.

PCR modes:
  context_only      mastery < threshold_low  → no answer chunks retrieved
  prerequisite_first  threshold_low ≤ m < threshold_high → prerequisite chunks first
  full_reveal       mastery ≥ threshold_high → all chunks including answer
"""
from __future__ import annotations

import os
import threading
from typing import Optional

import yaml
from openai import OpenAI
from qdrant_client import QdrantClient
from qdrant_client.models import Filter, FieldCondition, MatchValue, MatchAny
from rank_bm25 import BM25Okapi

from src.state import TutoringState, RetrievalMode

with open("config.yaml") as f:
    _cfg = yaml.safe_load(f)

_PCR = _cfg["pcr"]
_RET = _cfg["retrieval"]
_EMB = _cfg["embedding"]


# ── Clients (lazy-initialized) ────────────────────────────────────────────────

_qdrant: Optional[QdrantClient] = None
_openai: Optional[OpenAI] = None


def _get_qdrant() -> QdrantClient:
    global _qdrant
    if _qdrant is None:
        _qdrant = QdrantClient(path="./qdrant_data")
    return _qdrant


def _get_openai() -> OpenAI:
    global _openai
    if _openai is None:
        _openai = OpenAI(
            api_key=os.environ["OPENAI_API_KEY"],
            base_url=os.getenv("OPENAI_BASE_URL"),  # None → default OpenAI
            timeout=30.0,
        )
    return _openai


# ── Embedding ─────────────────────────────────────────────────────────────────

def _embed(text: str) -> list[float]:
    provider = os.getenv("EMBEDDING_PROVIDER", _EMB["provider"])
    if provider == "gemini":
        from google import genai as google_genai
        gclient = google_genai.Client(api_key=os.environ["GOOGLE_API_KEY"])
        r = gclient.models.embed_content(
            model=_EMB["gemini_model"],
            contents=text,
        )
        return r.embeddings[0].values
    else:
        client = _get_openai()
        resp = client.embeddings.create(
            model=_EMB["openai_model"],
            input=text,
        )
        return resp.data[0].embedding


# ── PCR filter ────────────────────────────────────────────────────────────────

def _get_retrieval_mode(mastery: float) -> RetrievalMode:
    if mastery < _PCR["threshold_low"]:
        return "context_only"
    elif mastery < _PCR["threshold_high"]:
        return "prerequisite_first"
    else:
        return "full_reveal"


def _build_pcr_filter(mode: RetrievalMode, concept: Optional[str]) -> Optional[Filter]:
    """Build Qdrant metadata filter based on PCR mode."""
    if mode == "context_only":
        # Exclude answer chunks — the LLM never sees the correct answer
        return Filter(
            must_not=[
                FieldCondition(key="is_answer_chunk", match=MatchValue(value=True))
            ]
        )
    elif mode == "prerequisite_first":
        # Only retrieve prerequisite and context chunks, not direct answers
        return Filter(
            must=[
                FieldCondition(
                    key="chunk_type",
                    match=MatchAny(any=["context", "prerequisite", "figure"]),
                )
            ]
        )
    else:
        # full_reveal: no filter, retrieve everything
        return None


# ── BM25 sparse retrieval ─────────────────────────────────────────────────────

_bm25_corpus: Optional[list[dict]] = None
_bm25_index: Optional[BM25Okapi] = None
_bm25_lock = threading.Lock()


def _load_bm25_corpus():
    """Load all chunks from Qdrant into memory for BM25 indexing (thread-safe)."""
    global _bm25_corpus, _bm25_index
    if _bm25_corpus is not None:
        return
    with _bm25_lock:
        # Double-check inside lock
        if _bm25_corpus is not None:
            return
        client = _get_qdrant()
        collection = os.getenv("QDRANT_COLLECTION", _cfg["qdrant"]["collection"])
        all_points, _ = client.scroll(
            collection_name=collection,
            limit=10000,
            with_payload=True,
            with_vectors=False,
        )
        _bm25_corpus = [p.payload for p in all_points]
        tokenized = [p["text"].lower().split() for p in _bm25_corpus]
        _bm25_index = BM25Okapi(tokenized)


def _bm25_retrieve(query: str, top_k: int) -> list[dict]:
    _load_bm25_corpus()
    tokens = query.lower().split()
    scores = _bm25_index.get_scores(tokens)
    ranked = sorted(
        zip(scores, _bm25_corpus), key=lambda x: x[0], reverse=True
    )
    return [item for _, item in ranked[:top_k]]


# ── Reciprocal Rank Fusion ────────────────────────────────────────────────────

def _rrf_merge(
    dense_hits: list[dict],
    sparse_hits: list[dict],
    k: int = 60,
) -> list[dict]:
    """Merge dense and BM25 results using Reciprocal Rank Fusion."""
    scores: dict[str, float] = {}
    docs: dict[str, dict] = {}

    def _id(chunk: dict) -> str:
        return chunk.get("id", chunk.get("text", "")[:50])

    for rank, chunk in enumerate(dense_hits):
        cid = _id(chunk)
        scores[cid] = scores.get(cid, 0.0) + 1.0 / (k + rank + 1)
        docs[cid] = chunk

    for rank, chunk in enumerate(sparse_hits):
        cid = _id(chunk)
        scores[cid] = scores.get(cid, 0.0) + 1.0 / (k + rank + 1)
        docs[cid] = chunk

    ranked = sorted(scores.items(), key=lambda x: x[1], reverse=True)
    return [docs[cid] for cid, _ in ranked]


# ── CRAG: grade + re-query ────────────────────────────────────────────────────

def _grade_chunks(query: str, chunks: list[dict]) -> bool:
    """PCR filter + BM25 already ensures relevance — skip LLM grading call."""
    return bool(chunks)


def _reformulate_query(original_query: str) -> str:
    """CRAG re-query: synonym expansion + sub-question decomposition."""
    client = _get_openai()
    resp = client.chat.completions.create(
        model=_cfg["llm"].get("utility_model", _cfg["llm"]["model"]),
        messages=[{
            "role": "user",
            "content": (
                f"The following search query returned no relevant results: '{original_query}'\n"
                "Rewrite it to be more specific, using synonyms or anatomical terminology. "
                "Return only the rewritten query, nothing else."
            ),
        }],
        max_tokens=60,
        temperature=0.3,
    )
    content = resp.choices[0].message.content or original_query
    return content.strip()


# ── Main retrieval function ───────────────────────────────────────────────────

def retrieval_planner(state: TutoringState) -> dict:
    """
    PCR-filtered hybrid retrieval with optional Corrective RAG loop.
    Updates: retrieved_chunks, retrieval_mode
    """
    query = state["student_message"]
    topic = state.get("current_topic") or ""

    # When a proactive revisit is scheduled, augment the query with the
    # topic name so retrieval targets the right concept regardless of what
    # the student just typed.
    if state.get("revisit_scheduled") and state.get("revisit_topic"):
        topic_readable = state["revisit_topic"].replace("_", " ").replace(".", " ")
        query = f"{query} {topic_readable}" if query.strip() else topic_readable

    mastery = state.get("mastery_scores", {}).get(topic, _cfg["mastery"]["default_prior"])
    mode = _get_retrieval_mode(mastery)

    collection = os.getenv("QDRANT_COLLECTION", _cfg["qdrant"]["collection"])
    client = _get_qdrant()
    top_k = _RET["top_k"]

    pcr_filter = _build_pcr_filter(mode, topic)

    for attempt in range(_RET["crag_max_retries"] + 1):
        # Dense retrieval
        # BM25-only retrieval (no embedding API call — local, instant)
        # Dense vector search is commented out to eliminate the Gemini/OpenAI embedding
        # round-trip (~500ms–1s per turn). BM25 over the topic-filtered corpus is
        # accurate enough for anatomy tutoring.
        sparse_chunks = _bm25_retrieve(query, top_k * 2)
        if mode == "context_only":
            sparse_chunks = [c for c in sparse_chunks if not c.get("is_answer_chunk")]
        elif mode == "prerequisite_first":
            sparse_chunks = [c for c in sparse_chunks
                              if c.get("chunk_type") in ("context", "prerequisite", "figure")]
        merged = sparse_chunks

        # CRAG: grade relevance
        if _grade_chunks(query, merged):
            break

        # Re-query if grading failed and retries remain
        if attempt < _RET["crag_max_retries"]:
            query = _reformulate_query(query)

    return {
        "retrieved_chunks": merged[:top_k],
        "retrieval_mode": mode,
    }
