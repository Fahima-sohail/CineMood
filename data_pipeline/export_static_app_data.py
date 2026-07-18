"""Build browser-ready CineMood data from the validated offline pipeline.

No TMDb or model calls happen here at runtime. Re-run this script after
regenerating the dataset, embeddings, or emotional timelines.
"""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np


PIPELINE_DIR = Path(__file__).resolve().parent
PROJECT_DIR = PIPELINE_DIR.parent
PUBLIC_DATA_DIR = PROJECT_DIR / "public" / "data"

MOVIES_FILE = PIPELINE_DIR / "movies.json"
CONTENT_EMBEDDINGS_FILE = PIPELINE_DIR / "movie_embeddings.npy"
KEYWORD_EMBEDDINGS_FILE = PIPELINE_DIR / "movie_keyword_embeddings.npy"
INDEX_FILE = PIPELINE_DIR / "movie_embedding_index.json"
CURVES_FILE = PIPELINE_DIR / "tension_curves.json"
SEARCH_CONFIG_FILE = PIPELINE_DIR / "search_config.json"

CONTENT_WEIGHT = 0.70
KEYWORD_WEIGHT = 0.30


def read_json(path: Path):
    with path.open(encoding="utf-8") as file:
        return json.load(file)


def size_mb(path: Path) -> float:
    return path.stat().st_size / (1024 * 1024)


def main() -> None:
    movies = read_json(MOVIES_FILE)
    index_payload = read_json(INDEX_FILE)
    # The validated embedding step stores metadata plus the row-to-movie mapping.
    index = index_payload.get("movie_ids") if isinstance(index_payload, dict) else index_payload
    curves = read_json(CURVES_FILE)
    content_embeddings = np.load(CONTENT_EMBEDDINGS_FILE)
    keyword_embeddings = np.load(KEYWORD_EMBEDDINGS_FILE)

    if not isinstance(movies, list):
        raise ValueError("movies.json must contain a list of movies.")
    if not isinstance(index, list):
        raise ValueError("movie_embedding_index.json must contain a movie_ids list.")
    if len(index) != len(content_embeddings) or len(index) != len(keyword_embeddings):
        raise ValueError("Embedding index and both embedding arrays must have the same number of rows.")

    movie_by_id = {str(movie["tmdb_id"]): movie for movie in movies}
    records = []
    for row, movie_id in enumerate(index):
        movie = movie_by_id.get(str(movie_id))
        if movie is None:
            raise ValueError(f"Embedding index references missing movie ID: {movie_id}")
        records.append({
            "id": movie["tmdb_id"],
            "title": movie["title"],
            "year": movie.get("year"),
            "genres": movie.get("genres", []),
            "runtime": movie.get("runtime"),
            "overview": movie.get("overview", ""),
            "poster_path": movie.get("poster_path"),
            "vote_average": movie.get("vote_average"),
            "vote_count": movie.get("vote_count"),
                "keywords": movie.get("keywords", []),
                "has_keywords": bool(movie.get("keywords")),
            "embedding": content_embeddings[row].astype(float).tolist(),
            "keyword_embedding": keyword_embeddings[row].astype(float).tolist(),
        })

    PUBLIC_DATA_DIR.mkdir(parents=True, exist_ok=True)
    movies_output = PUBLIC_DATA_DIR / "movies_data.json"
    curves_output = PUBLIC_DATA_DIR / "tension_curves.json"
    config_output = PUBLIC_DATA_DIR / "search_config.json"
    payload = {
        "model": "all-MiniLM-L6-v2",
        "normalized": True,
        "dimensions": int(content_embeddings.shape[1]),
        "content_weight": CONTENT_WEIGHT,
        "keyword_weight": KEYWORD_WEIGHT,
        "movies": records,
    }
    with movies_output.open("w", encoding="utf-8") as file:
        json.dump(payload, file, ensure_ascii=False, separators=(",", ":"))
    with curves_output.open("w", encoding="utf-8") as file:
        json.dump(curves, file, ensure_ascii=False, separators=(",", ":"))
    with SEARCH_CONFIG_FILE.open(encoding="utf-8") as source, config_output.open("w", encoding="utf-8") as destination:
        json.dump(json.load(source), destination, ensure_ascii=False, separators=(",", ":"))

    verified = sum(not curve.get("is_approximate", True) for curve in curves.values())
    print(f"Exported {len(records)} movies ({content_embeddings.shape[1]} dimensions each).")
    print(f"Verified subtitle curves: {verified}; estimated arcs: {len(curves) - verified}.")
    print(f"{movies_output}: {size_mb(movies_output):.2f} MB")
    print(f"{curves_output}: {size_mb(curves_output):.2f} MB")
    print("The files are suitable for direct static loading; let GitHub Pages apply HTTP compression.")


if __name__ == "__main__":
    main()
