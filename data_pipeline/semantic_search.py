"""Run calibrated hybrid semantic search over CineMood's local MiniLM movie index."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

import numpy as np
from sentence_transformers import SentenceTransformer

from search_engine import expand_query, load_config, rank


PIPELINE_DIR = Path(__file__).resolve().parent
MOVIES_FILE = PIPELINE_DIR / "movies.json"
EMBEDDINGS_FILE = PIPELINE_DIR / "movie_embeddings.npy"
KEYWORD_EMBEDDINGS_FILE = PIPELINE_DIR / "movie_keyword_embeddings.npy"
INDEX_FILE = PIPELINE_DIR / "movie_embedding_index.json"


def load_search_assets() -> tuple[list[dict[str, Any]], np.ndarray, np.ndarray, dict[str, Any]]:
    with MOVIES_FILE.open(encoding="utf-8") as file:
        movies_by_id = {int(movie["tmdb_id"]): movie for movie in json.load(file)}
    with INDEX_FILE.open(encoding="utf-8") as file:
        index = json.load(file)
    content, keywords = np.load(EMBEDDINGS_FILE), np.load(KEYWORD_EMBEDDINGS_FILE)
    movie_ids = index.get("movie_ids", [])
    if len(movie_ids) != len(content) or len(content) != len(keywords):
        raise ValueError("Movie IDs, content vectors, and keyword vectors are out of sync. Rebuild embeddings.")
    return [movies_by_id[int(movie_id)] for movie_id in movie_ids], content, keywords, index


def search_movies(query: str, model: SentenceTransformer, movies: list[dict[str, Any]], content: np.ndarray, keywords: np.ndarray, config: dict[str, Any], limit: int = 8) -> tuple[list[dict[str, Any]], bool, str]:
    expanded = expand_query(query, config)
    vector = model.encode(expanded, convert_to_numpy=True, normalize_embeddings=True)
    rows, should_empty = rank(query, vector, content, keywords, movies, config, limit)
    for row in rows:
        movie = movies[row.pop("position")]
        row.update({"title": movie["title"], "year": movie.get("year"), "tmdb_rating": movie.get("vote_average")})
    return rows, should_empty, expanded


def main() -> int:
    parser = argparse.ArgumentParser(description="Run calibrated hybrid MiniLM search over CineMood.")
    parser.add_argument("query")
    parser.add_argument("--limit", type=int, default=8)
    args = parser.parse_args()
    movies, content, keywords, index = load_search_assets()
    model = SentenceTransformer(index["model"], local_files_only=True)
    rows, should_empty, expanded = search_movies(args.query, model, movies, content, keywords, load_config(), args.limit)
    print(json.dumps({"query": args.query, "expanded_query": expanded, "show_empty": should_empty, "results": rows}, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
