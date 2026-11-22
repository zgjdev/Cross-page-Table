"""Conservative prefix edits for an image-derived, same-column bounded pilot."""

import hashlib
import re
from dataclasses import dataclass, replace

import numpy as np

from cptla.reconstruction.grid import Grid

# The edit action may remove only a leading prefix, never an entire fragment.
MAX_CUT = 3
MIN_CANDIDATE_SIMILARITY = 0.55
MIN_FRAGMENT_LABEL_SCORE = 0.75
MIN_LABEL_MARGIN = 0.02


@dataclass(frozen=True)
class Candidate:
    cut: int
    local: tuple[float, ...]
    context: tuple[float, ...]

    def vector(self, with_context):
        return self.local + self.context if with_context else self.local


def normalized_rows(grid):
    rows = [[""] * grid.n_cols for _ in range(grid.n_rows)]
    for cell in grid.cells:
        text = re.sub(r"\s+", " ", cell.text).strip().casefold()
        width = cell.col_end - cell.col_start
        for row in range(cell.row_start, cell.row_end):
            rows[row][cell.col_start : cell.col_end] = [text] * width
    return tuple(map(tuple, rows))


def _legal_cut(grid, cut):
    return (
        type(cut) is int
        and 0 <= cut <= MAX_CUT
        and cut < grid.n_rows
        and not any(cell.row_start < cut < cell.row_end for cell in grid.cells)
    )


def _prefix_similarity(left, right, cut):
    if len(left) < cut:
        return 0.0
    pairs = [
        (x, y)
        for a, b in zip(left[:cut], right[:cut], strict=True)
        for x, y in zip(a, b, strict=True)
    ]
    occupied = [(x, y) for x, y in pairs if x or y]
    return sum(x == y for x, y in occupied) / len(occupied) if occupied else 0.0


def boundary_candidates(grids):
    if len(grids) < 2 or len({grid.n_cols for grid in grids}) != 1:
        raise ValueError("pilot requires at least two equal-width fragments")
    rows = [normalized_rows(grid) for grid in grids]
    boundaries = []
    for index in range(1, len(grids)):
        prev, current = rows[index - 1], rows[index]
        candidates = [Candidate(0, (0.0,) * 9, (0.0,) * 4)]
        for cut in range(1, min(MAX_CUT + 1, len(current))):
            if not _legal_cut(grids[index], cut):
                continue
            previous = _prefix_similarity(prev, current, cut)
            earlier = [_prefix_similarity(r, current, cut) for r in rows[: index - 1]]
            later = [_prefix_similarity(r, current, cut) for r in rows[index + 1 :]]
            first = _prefix_similarity(rows[0], current, cut)
            terminal = _prefix_similarity(prev[-cut:], current, cut)
            if max((previous, *earlier)) < MIN_CANDIDATE_SIMILARITY:
                continue
            prefix_cells = [cell for cell in grids[index].cells if cell.row_start < cut]
            prefix_text = [text for row in current[:cut] for text in row if text]
            candidates.append(
                Candidate(
                    cut,
                    (
                        1.0,
                        cut / MAX_CUT,
                        previous,
                        float(previous == 1),
                        terminal,
                        sum(cell.header for cell in prefix_cells) / len(prefix_cells),
                        sum(any(c.isdigit() for c in t) for t in prefix_text) / len(prefix_text),
                        cut / len(current),
                        _prefix_similarity(prev[cut:], current[cut:], 1),
                    ),
                    (
                        first if index > 1 else 0.0,
                        sum(v == 1 for v in earlier) / max(len(earlier), 1),
                        max(later, default=0.0),
                        sum(v == 1 for v in later) / max(len(later), 1),
                    ),
                )
            )
        boundaries.append(candidates)
    return boundaries


def apply_cuts(grids, cuts):
    if len(grids) != len(cuts) + 1 or len({grid.n_cols for grid in grids}) != 1:
        raise ValueError("row actions require a cut per boundary and a common column count")
    cells = []
    row_count = 0
    for grid, cut in zip(grids, (0, *cuts), strict=True):
        if not _legal_cut(grid, cut):
            raise ValueError("cut would remove a whole fragment or cross a rowspan")
        cells.extend(
            replace(
                cell,
                row_start=cell.row_start - cut + row_count,
                row_end=cell.row_end - cut + row_count,
            )
            for cell in grid.cells
            if cell.row_start >= cut
        )
        row_count += grid.n_rows - cut
    return Grid(row_count, grids[0].n_cols, tuple(cells))


def _retained_text_agreement(fragment, target):
    occupied, matches = 0, 0
    for left, right in zip(fragment, target, strict=True):
        for x, y in zip(left, right, strict=True):
            occupied += bool(x or y)
            matches += bool(x and x == y)
    return matches / occupied if occupied else 0.0


def derive_weak_label(grids, boundaries, target):
    """Target content is used only offline. Keep two best paths per row endpoint."""
    if not grids or grids[0].n_cols != target.n_cols:
        return None
    truth = normalized_rows(target)
    states = {0: [(0.0, (), 1.0)]}
    for index, grid in enumerate(grids):
        rows = normalized_rows(grid)
        cuts = [cand.cut for cand in boundaries[index - 1]] if index else [0]
        updated = {}
        for start, paths in states.items():
            for cut in cuts:
                retained = rows[cut:]
                end = start + len(retained)
                if end > len(truth):
                    continue
                match = _retained_text_agreement(retained, truth[start:end])
                if match < MIN_FRAGMENT_LABEL_SCORE:
                    continue
                current = updated.setdefault(end, [])
                current.extend(
                    (score + match * len(retained), path + (cut,), min(worst, match))
                    for score, path, worst in paths
                )
                current.sort(reverse=True)
                del current[2:]
        states = updated
    best = states.get(len(truth), [])
    if not best:
        return None
    margin = (best[0][0] - best[1][0]) / len(truth) if len(best) > 1 else None
    if margin is not None and margin < MIN_LABEL_MARGIN:
        return None
    score, path, minimum = best[0]
    if score / len(truth) < 0.85:
        return None
    return {
        "cuts": path[1:],
        "weighted_agreement": score / len(truth),
        "min_fragment_agreement": minimum,
        "margin": margin,
        "audit_status": "unreviewed_weak_label",
    }


def split_groups(rows, seed):
    doc_to_cluster, clusters, seen = {}, {}, set()
    for row in rows:
        gid, doc, cluster = (row[k] for k in ("group_id", "document_id", "cluster_id"))
        if not all(isinstance(x, str) and x for x in (gid, doc, cluster)):
            raise ValueError("missing group, document or cluster identity")
        if gid in seen or doc_to_cluster.setdefault(doc, cluster) != cluster:
            raise ValueError("duplicate group or conflicting document cluster")
        seen.add(gid)
        clusters.setdefault(cluster, []).append(gid)
    if len(clusters) < 2:
        raise ValueError("at least two document clusters are required")
    ordered = sorted(
        clusters,
        key=lambda c: (hashlib.sha256(f"{seed}\0{c}".encode()).digest(), c),
    )
    n_dev = max(1, len(ordered) // 4)
    fit = sorted(g for c in ordered[n_dev:] for g in clusters[c])
    dev = sorted(g for c in ordered[:n_dev] for g in clusters[c])
    return fit, dev


def fit_ranker(examples, with_context):
    """Deterministic regularized linear conditional softmax over each boundary's actions."""
    choices = [
        (np.asarray([c.vector(with_context) for c in candidates]), winner)
        for candidates, winner in examples
        if len(candidates) > 1
    ]
    if not choices:
        raise ValueError("no informative weak-label training boundaries")
    weights = np.zeros(choices[0][0].shape[1])
    for _ in range(400):
        gradient = np.zeros_like(weights)
        for features, winner in choices:
            logits = features @ weights
            relative = np.exp(logits - np.max(logits))
            gradient += (relative / relative.sum()) @ features - features[winner]
        weights -= 0.15 * (gradient / len(choices) + 0.01 * weights)
    return weights


def predict_cuts(boundaries, weights, with_context):
    """Score candidates without target access. Ties preserve more rows."""
    return tuple(
        max(candidates, key=lambda c: (np.dot(c.vector(with_context), weights), -c.cut)).cut
        for candidates in boundaries
    )
