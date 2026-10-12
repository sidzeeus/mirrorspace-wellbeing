"""The curated knowledge base: chunking, embedding, indexing and retrieval.

Retrieval grounds answers in reviewed text. It is not model training, and it does not
by itself make the chat safe or clinically valid.

The embedder here is local and deterministic: it hashes words and word pairs into a
256-number vector (a "hashing" bag-of-words). That means no student text is sent to an
embedding provider at all, tests need no network, and results are reproducible. It
matches on shared vocabulary, not meaning, so it is a starting point. Replacing it
with a semantic embedding model means changing `embed` and the vector size in
`models.EMBEDDING_DIMENSIONS`, then re-running `index_knowledge`.
"""

from __future__ import annotations

import hashlib
import math
import re
from dataclasses import dataclass

from django.conf import settings
from django.db import transaction
from pgvector.django import CosineDistance

from apps.wellbeing.models import visible_statuses

from .models import EMBEDDING_DIMENSIONS, ContentChunk, ContentDocument

CHUNK_WORDS = 90
TOP_K = 3
# A passage is only used if it shares at least this many distinct terms with the
# question. Below that the chat says it has no reviewed material, and no model is asked.
MIN_SHARED_TERMS = 2
# How many nearest passages are considered before that rule is applied.
CANDIDATES = 8

_WORD = re.compile(r"[a-zऀ-ॿ]{3,}")
_STOPWORDS = frozenset(
    [
        "the",
        "and",
        "for",
        "are",
        "but",
        "not",
        "you",
        "your",
        "with",
        "this",
        "that",
        "have",
        "has",
        "had",
        "was",
        "were",
        "what",
        "when",
        "how",
        "why",
        "can",
        "could",
        "would",
        "should",
        "will",
        "about",
        "from",
        "they",
        "them",
        "their",
        "there",
        "then",
        "than",
        "into",
        "out",
        "get",
        "got",
        "any",
        "all",
        "some",
        "more",
        "most",
        "very",
        "just",
        "like",
        "feel",
        "feeling",
        "does",
        "did",
        "doing",
        "been",
        "being",
        "its",
        "our",
        "many",
        "much",
        "need",
        "needs",
        "usually",
        "also",
        "really",
        "thing",
        "things",
        "something",
    ]  # noqa: SIM905 - a readable word list
)
_SUFFIXES = ("ing", "ed", "s")


def _stem(word: str) -> str:
    """Very light stemming so "exams" meets "exam" and "stressed" meets "stress"."""
    for suffix in _SUFFIXES:
        if word.endswith(suffix) and len(word) - len(suffix) >= 4:
            return word[: -len(suffix)]
    return word


def _tokens(text: str) -> list[str]:
    return [_stem(word) for word in _WORD.findall(text.lower()) if word not in _STOPWORDS]


def embed(text: str) -> list[float]:
    """A unit vector built by hashing each word and neighbouring word pair."""
    vector = [0.0] * EMBEDDING_DIMENSIONS
    words = _tokens(text)
    features = words + [f"{a} {b}" for a, b in zip(words, words[1:], strict=False)]
    for feature in features:
        digest = hashlib.blake2b(feature.encode(), digest_size=8).digest()
        index = int.from_bytes(digest[:4], "big") % EMBEDDING_DIMENSIONS
        sign = 1.0 if digest[4] & 1 else -1.0
        vector[index] += sign
    norm = math.sqrt(sum(value * value for value in vector))
    return [value / norm for value in vector] if norm else vector


def chunk(body: str) -> list[str]:
    """Split a document into passages of roughly CHUNK_WORDS words, on paragraphs."""
    passages: list[str] = []
    current: list[str] = []
    count = 0
    for paragraph in (p.strip() for p in body.split("\n\n")):
        if not paragraph:
            continue
        words = len(paragraph.split())
        if current and count + words > CHUNK_WORDS:
            passages.append("\n\n".join(current))
            current, count = [], 0
        current.append(paragraph)
        count += words
    if current:
        passages.append("\n\n".join(current))
    return passages


@transaction.atomic
def index_document(document: ContentDocument) -> int:
    """Rebuild a document's passages. Unapproved documents end up with none."""
    ContentChunk.objects.filter(document=document).delete()
    if document.review_status not in visible_statuses():
        return 0
    passages = chunk(document.body)
    ContentChunk.objects.bulk_create(
        ContentChunk(
            document=document,
            position=position,
            text=text,
            embedding=embed(f"{document.title}\n{text}"),
        )
        for position, text in enumerate(passages)
    )
    return len(passages)


def index_all() -> dict[str, int]:
    indexed = skipped = passages = 0
    for document in ContentDocument.objects.all():
        created = index_document(document)
        passages += created
        if created:
            indexed += 1
        else:
            skipped += 1
    return {"documents_indexed": indexed, "documents_skipped": skipped, "passages": passages}


@dataclass(frozen=True)
class Passage:
    text: str
    title: str
    source: str
    slug: str


def retrieve(question: str, language: str) -> list[Passage]:
    """The few reviewed passages closest to the question, or none if nothing is close.

    The approval filter is applied again here, at query time, so a document that was
    un-approved after indexing can never be quoted.
    """
    terms = set(_tokens(question))
    if len(terms) < MIN_SHARED_TERMS:
        return []
    languages = {language, settings.LANGUAGE_CODE}
    candidates = (
        ContentChunk.objects.retrievable()
        .filter(document__language__in=languages)
        .annotate(distance=CosineDistance("embedding", embed(question)))
        .select_related("document")
        .order_by("distance")[:CANDIDATES]
    )
    matches = [
        candidate
        for candidate in candidates
        if len(terms & set(_tokens(f"{candidate.document.title} {candidate.text}")))
        >= MIN_SHARED_TERMS
    ][:TOP_K]
    return [
        Passage(
            text=match.text,
            title=match.document.title,
            source=match.document.source,
            slug=match.document.slug,
        )
        for match in matches
    ]
