"""Shared search-calibration rules for CineMood's offline validation tools."""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

import numpy as np


CONFIG_FILE = Path(__file__).resolve().parent / "search_config.json"
STOP_WORDS = {"a", "an", "the", "about", "and", "of", "in", "on", "to", "with", "for", "from", "that", "this", "it", "is", "are", "make"}
STRUCTURED_QUERY = re.compile(r"^(?:(?:a|an)\s+)?(musical|documentary)\s+about\s+(.+)$", re.IGNORECASE)


def load_config() -> dict[str, Any]:
    with CONFIG_FILE.open(encoding="utf-8") as file:
        return json.load(file)


def expand_query(query: str, config: dict[str, Any]) -> str:
    """Append a small, transparent intent vocabulary without naming any films."""
    normalized = query.lower()
    additions = [
        rule["append"]
        for rule in config["expansions"]
        if any(term in normalized for term in rule.get("terms", []))
        or (rule.get("all_terms") and all(term in normalized for term in rule["all_terms"]))
    ]
    return " ".join([query, *additions]) if additions else query


def hybrid_scores(query_vector: np.ndarray, content_vectors: np.ndarray, keyword_vectors: np.ndarray, movies: list[dict[str, Any]], config: dict[str, Any]) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    content_scores = content_vectors @ query_vector
    keyword_scores = keyword_vectors @ query_vector
    has_keywords = np.asarray([bool(movie.get("keywords")) for movie in movies])
    combined = config["content_weight"] * content_scores + config["keyword_weight"] * keyword_scores
    # Missing TMDb keywords never lower a movie's score.
    return np.where(has_keywords, combined, content_scores), content_scores, keyword_scores


def confidence_band(score: float, top_scores: np.ndarray) -> tuple[str, int]:
    """Confidence is relative to the top result set, never an absolute cosine cutoff."""
    highest, lowest = float(top_scores[0]), float(top_scores[-1])
    relative = (score - lowest) / max(highest - lowest, 1e-6)
    if relative >= .67:
        label = "High confidence"
    elif relative >= .34:
        label = "Medium confidence"
    else:
        label = "Low confidence"
    return label, round(54 + 42 * max(0.0, min(1.0, relative)))


def _movie_text(movie: dict[str, Any]) -> str:
    return " ".join([movie.get("title", ""), movie.get("overview", ""), *movie.get("genres", []), *movie.get("keywords", [])]).lower()


def should_show_empty(query: str, top_positions: np.ndarray, all_scores: np.ndarray, movies: list[dict[str, Any]], config: dict[str, Any]) -> bool:
    """Reject only a clearly unsupported structured request or a very weak entire result set."""
    match = STRUCTURED_QUERY.match(query.strip())
    if match:
        requested_genre, subject = match.groups()
        genre_words = config["structured_genres"].get(requested_genre.lower(), [requested_genre.lower()])
        subject_words = [word for word in re.findall(r"[a-z]{3,}", subject.lower()) if word not in STOP_WORDS]
        # A genre + topic request needs at least one candidate that can support both ideas.
        has_joint_match = any(
            any(word in " ".join(movies[int(position)].get("genres", []) if requested_genre.lower() == "documentary" else [*movies[int(position)].get("genres", []), *movies[int(position)].get("keywords", [])]).lower() for word in genre_words)
            and all(word in _movie_text(movies[int(position)]) for word in subject_words)
            for position in top_positions
        )
        if not has_joint_match:
            return True

    top_scores = all_scores[top_positions]
    # Conservative fallback for a query that is low both absolutely and relative to its corpus distribution.
    return bool(top_scores[0] < .14 and (top_scores[0] - float(all_scores.mean())) < .06)


def rank(query: str, query_vector: np.ndarray, content_vectors: np.ndarray, keyword_vectors: np.ndarray, movies: list[dict[str, Any]], config: dict[str, Any], limit: int = 8) -> tuple[list[dict[str, Any]], bool]:
    scores, content_scores, keyword_scores = hybrid_scores(query_vector, content_vectors, keyword_vectors, movies, config)
    positions = np.argsort(scores)[::-1]
    top_ten = positions[:10]
    top_results = positions[:limit]
    reference_scores = scores[top_results]
    rows = []
    for position in top_results:
        label, percentage = confidence_band(float(scores[position]), reference_scores)
        rows.append({
            "position": int(position),
            "score": float(scores[position]),
            "content_score": float(content_scores[position]),
            "keyword_score": float(keyword_scores[position]),
            "has_keywords": bool(movies[int(position)].get("keywords")),
            "confidence_label": label,
            "confidence_percentage": percentage,
        })
    return rows, should_show_empty(query, top_ten, scores, movies, config)
