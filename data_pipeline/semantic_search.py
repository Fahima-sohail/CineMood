"""Search CineMood's local sentence-transformer movie index from the terminal."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

import numpy as np
from sentence_transformers import SentenceTransformer


PIPELINE_DIR = Path(__file__).resolve().parent
MOVIES_FILE = PIPELINE_DIR / "movies.json"
EMBEDDINGS_FILE = PIPELINE_DIR / "movie_embeddings.npy"
INDEX_FILE = PIPELINE_DIR / "movie_embedding_index.json"
EXAMPLE_QUERIES = [
    "a love story that feels like a long conversation",
    "a quiet devastating ending",
    "chaotic fun heist energy",
    "a father protecting his family against all odds",
]


def load_search_assets(
    movies_path: Path = MOVIES_FILE,
    embeddings_path: Path = EMBEDDINGS_FILE,
    index_path: Path = INDEX_FILE,
) -> tuple[dict[int, dict[str, Any]], np.ndarray, dict[str, Any]]:
    if not embeddings_path.exists() or not index_path.exists():
        raise FileNotFoundError("Embeddings are missing. Run: py data_pipeline/build_embeddings.py")
    with movies_path.open("r", encoding="utf-8") as file:
        movies = {int(movie["tmdb_id"]): movie for movie in json.load(file)}
    with index_path.open("r", encoding="utf-8") as file:
        index = json.load(file)
    embeddings = np.load(embeddings_path)
    ids = index.get("movie_ids", [])
    if len(ids) != len(embeddings):
        raise ValueError("Embedding index and matrix length differ. Rebuild embeddings.")
    return movies, embeddings, index


def search_movies(
    query: str,
    model: SentenceTransformer,
    movies_by_id: dict[int, dict[str, Any]],
    embeddings: np.ndarray,
    index: dict[str, Any],
    limit: int = 5,
) -> tuple[list[dict[str, Any]], np.ndarray]:
    """Return top results using cosine similarity (dot product of normalized vectors)."""
    query_vector = model.encode(query, convert_to_numpy=True, normalize_embeddings=True)
    scores = embeddings @ query_vector
    top_positions = np.argsort(scores)[::-1][:limit]
    results = []
    for position in top_positions:
        movie_id = int(index["movie_ids"][int(position)])
        movie = movies_by_id[movie_id]
        results.append({"title": movie["title"], "year": movie.get("year"), "score": float(scores[position]), "genres": movie.get("genres", []), "tmdb_rating": movie.get("vote_average")})
    return results, scores


def print_examples(model: SentenceTransformer, movies: dict[int, dict[str, Any]], embeddings: np.ndarray, index: dict[str, Any]) -> None:
    all_scores: list[float] = []
    for query in EXAMPLE_QUERIES:
        results, scores = search_movies(query, model, movies, embeddings, index, limit=5)
        all_scores.extend(scores.tolist())
        print(f"\nQuery: {query!r}")
        print(f"Score distribution — min {scores.min():.3f} | avg {scores.mean():.3f} | max {scores.max():.3f}")
        for rank, result in enumerate(results, start=1):
            print(f"  {rank}. {result['title']} ({result['year']}) — {result['score']:.3f} | TMDb {result['tmdb_rating']}")
    distribution = np.asarray(all_scores)
    print("\nCombined distribution across all example-query/movie comparisons:")
    print(f"min {distribution.min():.3f} | avg {distribution.mean():.3f} | max {distribution.max():.3f}")


def main() -> int:
    parser = argparse.ArgumentParser(description="Run local semantic search over CineMood embeddings.")
    parser.add_argument("--query", help="One query to run instead of the built-in test suite.")
    parser.add_argument("--limit", type=int, default=5)
    args = parser.parse_args()
    movies, embeddings, index = load_search_assets()
    model_name = index.get("model", "all-MiniLM-L6-v2")
    print(f"Loading {model_name}; searching {len(embeddings)} normalized movie embeddings…")
    # Embeddings and model must always be paired; loading from the local cache
    # prevents an unnecessary network check on every terminal search.
    model = SentenceTransformer(model_name, local_files_only=True)
    if args.query:
        results, scores = search_movies(args.query, model, movies, embeddings, index, limit=args.limit)
        print(f"\nQuery: {args.query!r}")
        print(f"Score distribution — min {scores.min():.3f} | avg {scores.mean():.3f} | max {scores.max():.3f}")
        for rank, result in enumerate(results, start=1):
            print(f"  {rank}. {result['title']} ({result['year']}) — {result['score']:.3f} | TMDb {result['tmdb_rating']}")
    else:
        print_examples(model, movies, embeddings, index)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
