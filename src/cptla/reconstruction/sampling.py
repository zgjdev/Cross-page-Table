"""Provisional document grouping and stratified audit sampling."""

import re
import unicodedata
from collections import Counter, defaultdict
from hashlib import blake2b, sha256
from heapq import nsmallest
from html import unescape

_SPLITS = ("train_fit", "train_dev", "train_confirm")
_BANDS = 4
_BAND_BITS = 16
_SHINGLE_SIZE = 5
_MIN_TOKENS = 50
_MAX_HAMMING = 3
_MIN_JACCARD = 0.85
_SKETCH_SIZE = 256


def _normalize(text: str) -> str:
    without_tags = re.sub(r"</?[a-zA-Z][^<>]*>", " ", text)
    return " ".join(unicodedata.normalize("NFKC", unescape(without_tags)).casefold().split())


def _shingles(tokens: list[str]) -> set[str]:
    return {
        " ".join(tokens[index : index + _SHINGLE_SIZE])
        for index in range(len(tokens) - _SHINGLE_SIZE + 1)
    }


def _simhash(tokens: list[str]) -> int:
    hashes = (blake2b(shingle.encode(), digest_size=16).digest() for shingle in _shingles(tokens))
    # Rank with the leading half and vote with the trailing half to avoid low-bit-pattern bias.
    sketch = [int.from_bytes(value[8:], "big") for value in nsmallest(_SKETCH_SIZE, hashes)]
    return sum(
        1 << bit
        for bit in range(_BANDS * _BAND_BITS)
        if sum((value >> bit) & 1 for value in sketch) * 2 > len(sketch)
    )


def _seeded_hash(seed: int, purpose: str, key: str) -> int:
    return int.from_bytes(sha256(f"{seed}:{purpose}:{key}".encode()).digest(), "big")


def group_and_split(documents: list[dict], *, seed: int = 20261109) -> dict:
    """Group table-text duplicates within official train before assigning splits."""
    normalized = {doc["document_id"]: _normalize(doc["text"]) for doc in documents}
    if len(normalized) != len(documents):
        raise ValueError("Duplicate document_id")
    parents = {document_id: document_id for document_id in normalized}

    def find(document_id: str) -> str:
        while parents[document_id] != document_id:
            parents[document_id] = parents[parents[document_id]]
            document_id = parents[document_id]
        return document_id

    def join(left: str, right: str) -> None:
        first, second = sorted((find(left), find(right)))
        parents[second] = first

    exact = {}
    fingerprints = {}
    buckets = defaultdict(list)
    candidates = []
    for document_id, text in sorted(normalized.items()):
        if not text:
            continue
        if text in exact:
            representative = exact[text]
            join(representative, document_id)
            candidates.append(
                {
                    "left_document_id": representative,
                    "right_document_id": document_id,
                    "kind": "exact_text",
                    "accepted": True,
                }
            )
            continue

        exact[text] = document_id
        tokens = text.split()
        if len(tokens) < _MIN_TOKENS:
            continue
        fingerprint = _simhash(tokens)
        fingerprints[document_id] = fingerprint
        possible_matches = set()
        for band in range(_BANDS):
            key = (band, (fingerprint >> (band * _BAND_BITS)) & ((1 << _BAND_BITS) - 1))
            possible_matches.update(buckets[key])
            buckets[key].append(document_id)

        current_shingles = None
        for other in sorted(possible_matches):
            hamming = (fingerprint ^ fingerprints[other]).bit_count()
            jaccard = None
            if hamming <= _MAX_HAMMING:
                if current_shingles is None:
                    current_shingles = _shingles(tokens)
                previous_shingles = _shingles(normalized[other].split())
                intersection = len(current_shingles & previous_shingles)
                jaccard = intersection / (
                    len(current_shingles) + len(previous_shingles) - intersection
                )
            accepted = jaccard is not None and jaccard >= _MIN_JACCARD
            if accepted:
                join(other, document_id)
            candidates.append(
                {
                    "left_document_id": other,
                    "right_document_id": document_id,
                    "kind": "simhash_band",
                    "hamming": hamming,
                    "jaccard": jaccard,
                    "accepted": accepted,
                }
            )

    assignments = []
    for document_id in sorted(normalized):
        cluster_id = find(document_id)
        value = _seeded_hash(seed, "split", cluster_id)
        scale = 1 << 256
        bucket = 0 if value * 100 < scale * 70 else 1 if value * 100 < scale * 85 else 2
        assignments.append(
            {
                "document_id": document_id,
                "cluster_id": cluster_id,
                "split": _SPLITS[bucket],
            }
        )

    counts = Counter(row["split"] for row in assignments)
    return {
        "assignments": assignments,
        "duplicate_candidates": candidates,
        "summary": {
            "split_status": "provisional_do_not_train",
            "source_scope": "official_train_table_text_only",
            "seed": seed,
            "document_count": len(assignments),
            "cluster_count": len({row["cluster_id"] for row in assignments}),
            "split_counts": {split: counts[split] for split in _SPLITS},
            "split_fractions": {
                split: counts[split] / len(assignments) if assignments else 0.0 for split in _SPLITS
            },
            "candidate_count": len(candidates),
            "accepted_edge_count": sum(row["accepted"] for row in candidates),
            "parameters": {
                "shingle_size": _SHINGLE_SIZE,
                "min_tokens": _MIN_TOKENS,
                "simhash_bits": _BANDS * _BAND_BITS,
                "bands": _BANDS,
                "band_bits": _BAND_BITS,
                "bottom_k": _SKETCH_SIZE,
                "max_hamming": _MAX_HAMMING,
                "min_jaccard": _MIN_JACCARD,
            },
            "limitations": [
                "Table text excludes document prose and page images.",
                "Sketching and the Hamming cutoff can miss high-Jaccard pairs.",
                "Visual and cross-official-split duplication audits are pending.",
                "Human threshold calibration is pending.",
            ],
        },
    }


def _balanced_selection(strata: dict, size: int, seed: int, purpose: str) -> dict:
    """Allocate one slot per active stratum per round, redistributing unused slots."""
    ordered = {
        stratum: sorted(
            rows, key=lambda row: (_seeded_hash(seed, purpose, row["group_id"]), row["group_id"])
        )
        for stratum, rows in sorted(strata.items())
    }
    priority = sorted(
        ordered, key=lambda name: (_seeded_hash(seed, f"{purpose}-stratum", name), name)
    )
    quotas = dict.fromkeys(ordered, 0)
    remaining = min(size, sum(map(len, ordered.values())))
    while remaining:
        for stratum in priority:
            if quotas[stratum] < len(ordered[stratum]):
                quotas[stratum] += 1
                remaining -= 1
                if not remaining:
                    break
    return {stratum: rows[: quotas[stratum]] for stratum, rows in ordered.items()}


def sample_audit_groups(
    profiles: list[dict],
    assignments: list[dict],
    *,
    sample_size: int = 200,
    coordinate_size: int = 20,
    seed: int = 20261109,
) -> dict:
    """Sample cross-page tables within provisional train_fit strata."""
    if sample_size < 0 or coordinate_size < 0:
        raise ValueError("Sample sizes must be nonnegative")
    splits = {row["document_id"]: row["split"] for row in assignments}
    if len(splits) != len(assignments):
        raise ValueError("Duplicate document_id in assignments")
    if len({row["group_id"] for row in profiles}) != len(profiles):
        raise ValueError("Duplicate group_id in profiles")

    population = defaultdict(list)
    for profile in profiles:
        if splits[profile["document_id"]] != "train_fit" or profile["page_count"] < 2:
            continue
        pages = str(profile["page_count"]) if profile["page_count"] < 4 else "4+"
        span = "span" if profile["has_span"] else "no_span"
        population[f"{pages}_pages_{span}"].append(profile)

    selected = _balanced_selection(population, sample_size, seed, "audit")
    coordinate = _balanced_selection(selected, coordinate_size, seed, "coordinate")
    samples = []
    strata = {}
    for stratum, rows in selected.items():
        total = len(population[stratum])
        count = len(rows)
        strata[stratum] = {
            "population": total,
            "sample_count": count,
            "coordinate_count": len(coordinate[stratum]),
            "inclusion_probability": count / total,
            "weight": total / count if count else None,
        }
        for row in rows:
            samples.append(
                {
                    **row,
                    "stratum": stratum,
                    "inclusion_probability": count / total,
                    "weight": total / count,
                }
            )

    coordinate_ids = [row["group_id"] for rows in coordinate.values() for row in rows]
    return {
        "samples": samples,
        "coordinate_group_ids": coordinate_ids,
        "strata": strata,
        "summary": {
            "source_split": "train_fit",
            "seed": seed,
            "population_count": sum(map(len, population.values())),
            "requested_sample_size": sample_size,
            "sample_count": len(samples),
            "sample_shortfall": sample_size - len(samples),
            "requested_coordinate_size": coordinate_size,
            "coordinate_count": len(coordinate_ids),
            "coordinate_shortfall": coordinate_size - len(coordinate_ids),
            "coordinate_role": "diagnostic_only",
            "audit_status": "pending",
        },
    }
