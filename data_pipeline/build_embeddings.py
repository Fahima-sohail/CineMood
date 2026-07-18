"""Generate normalized all-MiniLM-L6-v2 embeddings for CineMood movie text.

Outputs:
    movie_embeddings.npy          float32 matrix, one normalized vector per movie
    movie_embedding_index.json    metadata and row-to-TMDb-ID mapping
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
from sentence_transformers import SentenceTransformer


PIPELINE_DIR = Path(__file__).resolve().parent
DEFAULT_MOVIES = PIPELINE_DIR / "movies.json"
DEFAULT_EMBEDDINGS = PIPELINE_DIR / "movie_embeddings.npy"
DEFAULT_INDEX = PIPELINE_DIR / "movie_embedding_index.json"
MODEL_NAME = "all-MiniLM-L6-v2"


def load_movies(path: Path) -> list[dict]:
    with path.open("r", encoding="utf-8") as file:
        movies = json.load(file)
    valid_movies = [movie for movie in movies if movie.get("tmdb_id") and movie.get("combined_text", "").strip()]
    if not valid_movies:
        raise ValueError(f"No movies with tmdb_id and combined_text found in {path}")
    return valid_movies


def build_embeddings(movies: list[dict], model_name: str, batch_size: int) -> np.ndarray:
    """Embed overview + review text and L2-normalize for dot-product cosine search."""
    # Prefer the local cache. On a fresh machine, download once and retain it
    # in Hugging Face's cache; every later build works without a network check.
    try:
        model = SentenceTransformer(model_name, local_files_only=True)
    except OSError:
        print(f"Downloading {model_name} once for the local model cache…")
        model = SentenceTransformer(model_name)
    texts = [movie["combined_text"] for movie in movies]
    vectors = model.encode(
        texts,
        batch_size=batch_size,
        show_progress_bar=True,
        convert_to_numpy=True,
        normalize_embeddings=True,
    )
    return np.asarray(vectors, dtype=np.float32)


def main() -> int:
    parser = argparse.ArgumentParser(description="Build normalized embeddings for CineMood movies.")
    parser.add_argument("--movies", type=Path, default=DEFAULT_MOVIES)
    parser.add_argument("--embeddings", type=Path, default=DEFAULT_EMBEDDINGS)
    parser.add_argument("--index", type=Path, default=DEFAULT_INDEX)
    parser.add_argument("--model", default=MODEL_NAME)
    parser.add_argument("--batch-size", type=int, default=32)
    args = parser.parse_args()

    movies = load_movies(args.movies)
    print(f"Loading {args.model} and embedding {len(movies)} movies from {args.movies}…")
    embeddings = build_embeddings(movies, args.model, args.batch_size)
    args.embeddings.parent.mkdir(parents=True, exist_ok=True)
    np.save(args.embeddings, embeddings)
    index_payload = {
        "model": args.model,
        "normalized": True,
        "dimensions": int(embeddings.shape[1]),
        "movie_ids": [int(movie["tmdb_id"]) for movie in movies],
    }
    with args.index.open("w", encoding="utf-8") as file:
        json.dump(index_payload, file, indent=2)
        file.write("\n")
    print(f"Saved {embeddings.shape[0]} × {embeddings.shape[1]} embeddings to {args.embeddings}")
    print(f"Saved ID index to {args.index}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
