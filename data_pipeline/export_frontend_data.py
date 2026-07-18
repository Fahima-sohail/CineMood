"""Export the offline CineMood corpus and MiniLM vectors as one browser-ready JSON file.

This is a build-time-only step. The generated file is static and contains no
TMDb API key or runtime API dependency.
"""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np


PROJECT_ROOT = Path(__file__).resolve().parents[1]
PIPELINE_DIR = Path(__file__).resolve().parent
MOVIES_PATH = PIPELINE_DIR / "movies.json"
EMBEDDINGS_PATH = PIPELINE_DIR / "movie_embeddings.npy"
INDEX_PATH = PIPELINE_DIR / "movie_embedding_index.json"
OUTPUT_PATH = PROJECT_ROOT / "public" / "data" / "movies_data.json"


def main() -> int:
    with MOVIES_PATH.open("r", encoding="utf-8") as file:
        movies = {int(movie["tmdb_id"]): movie for movie in json.load(file)}
    with INDEX_PATH.open("r", encoding="utf-8") as file:
        index = json.load(file)
    embeddings = np.load(EMBEDDINGS_PATH)
    movie_ids = [int(movie_id) for movie_id in index["movie_ids"]]

    if len(movie_ids) != len(embeddings):
        raise ValueError("Embedding index and vector matrix have different row counts. Rebuild embeddings first.")
    if any(movie_id not in movies for movie_id in movie_ids):
        raise ValueError("Embedding index references movie IDs missing from movies.json. Rebuild embeddings first.")

    records = []
    for movie_id, embedding in zip(movie_ids, embeddings, strict=True):
        movie = movies[movie_id]
        records.append(
            {
                "id": movie_id,
                "title": movie["title"],
                "year": movie.get("year"),
                "genres": movie.get("genres", []),
                "runtime": movie.get("runtime"),
                "overview": movie.get("overview", ""),
                "poster_path": movie.get("poster_path"),
                "vote_average": movie.get("vote_average"),
                "vote_count": movie.get("vote_count"),
                "embedding": embedding.astype(float).tolist(),
            }
        )

    payload = {
        "model": index.get("model", "all-MiniLM-L6-v2"),
        "normalized": bool(index.get("normalized", True)),
        "dimensions": int(index.get("dimensions", embeddings.shape[1])),
        "movies": records,
    }
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    with OUTPUT_PATH.open("w", encoding="utf-8") as file:
        json.dump(payload, file, ensure_ascii=False, separators=(",", ":"))
    print(f"Exported {len(records)} movies with {payload['dimensions']}-dimensional vectors to {OUTPUT_PATH}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
