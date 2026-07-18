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
DEFAULT_KEYWORD_EMBEDDINGS = PIPELINE_DIR / "movie_keyword_embeddings.npy"
DEFAULT_INDEX = PIPELINE_DIR / "movie_embedding_index.json"
MODEL_NAME = "all-MiniLM-L6-v2"


def load_movies(path: Path) -> list[dict]:
    with path.open("r", encoding="utf-8") as file:
        movies = json.load(file)
    valid_movies = [movie for movie in movies if movie.get("tmdb_id") and movie.get("combined_text", "").strip()]
    if not valid_movies:
        raise ValueError(f"No movies with tmdb_id and combined_text found in {path}")
    return valid_movies


def load_model(model_name: str) -> SentenceTransformer:
    # Prefer the local cache. On a fresh machine, download once and retain it
    # in Hugging Face's cache; every later build works without a network check.
    try:
        return SentenceTransformer(model_name, local_files_only=True)
    except OSError:
        print(f"Downloading {model_name} once for the local model cache…")
        return SentenceTransformer(model_name)


def embed_texts(model: SentenceTransformer, texts: list[str], batch_size: int) -> np.ndarray:
    """L2-normalize vectors so a dot product is cosine similarity."""
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
    parser.add_argument("--keyword-embeddings", type=Path, default=DEFAULT_KEYWORD_EMBEDDINGS)
    parser.add_argument("--index", type=Path, default=DEFAULT_INDEX)
    parser.add_argument("--model", default=MODEL_NAME)
    parser.add_argument("--batch-size", type=int, default=32)
    args = parser.parse_args()

    movies = load_movies(args.movies)
    print(f"Loading {args.model} and embedding {len(movies)} movies from {args.movies}…")
    model = load_model(args.model)
    embeddings = embed_texts(model, [movie["combined_text"] for movie in movies], args.batch_size)
    # Do not fabricate a generic keyword vector for films that have no TMDb keywords.
    # Those rows intentionally remain zero vectors and search falls back to content-only.
    keyword_embeddings = np.zeros_like(embeddings)
    keyword_rows = [index for index, movie in enumerate(movies) if movie.get("keywords")]
    if keyword_rows:
        keyword_texts = [" ".join(movies[index]["keywords"]) for index in keyword_rows]
        keyword_embeddings[keyword_rows] = embed_texts(model, keyword_texts, args.batch_size)
    args.embeddings.parent.mkdir(parents=True, exist_ok=True)
    np.save(args.embeddings, embeddings)
    np.save(args.keyword_embeddings, keyword_embeddings)
    index_payload = {
        "model": args.model,
        "normalized": True,
        "dimensions": int(embeddings.shape[1]),
        "keyword_embeddings_file": args.keyword_embeddings.name,
        "keyword_embedding_rows": keyword_rows,
        "movie_ids": [int(movie["tmdb_id"]) for movie in movies],
    }
    with args.index.open("w", encoding="utf-8") as file:
        json.dump(index_payload, file, indent=2)
        file.write("\n")
    print(f"Saved {embeddings.shape[0]} × {embeddings.shape[1]} embeddings to {args.embeddings}")
    print(f"Saved {keyword_embeddings.shape[0]} × {keyword_embeddings.shape[1]} keyword embeddings to {args.keyword_embeddings}")
    print(f"Saved ID index to {args.index}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
