"""Audit CineMood's current offline search corpus before scoring changes."""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
from sentence_transformers import SentenceTransformer


ROOT = Path(__file__).resolve().parent.parent
PIPELINE = ROOT / "data_pipeline"
SAMPLE_SENTENCE = "a slow burn romance where they just talk all night"
QUERIES = [
    "a slow burn romance where they just talk all night",
    "nothing is what it seems",
    "hopeful but kind of sad at the same time",
    "second chance love story",
    "getting over a breakup but making it cute",
    "rich people behaving badly",
    "a dream within a dream kind of confusion",
    "cozy but makes you cry",
    "something to watch when I'm sick and want to feel less alone",
    "long distance relationship but make it space",
    "a musical about time travel",
    "falling in love with someone you're not supposed to",
    "a love story that breaks your heart at the end",
    "a twist I didn't see coming",
    "an unreliable narrator",
    "big scale but still feels personal",
    "a movie that makes prison feel hopeful somehow",
    "documentary about deep sea creatures",
]


def load_json(path: Path):
    with path.open(encoding="utf-8") as file:
        return json.load(file)


def format_results(scores: np.ndarray, movies: list[dict], limit: int = 10) -> list[dict]:
    order = np.argsort(scores)[::-1][:limit]
    return [
        {
            "rank": rank,
            "title": movies[position]["title"],
            "score": round(float(scores[position]), 4),
        }
        for rank, position in enumerate(order, start=1)
    ]


def main() -> None:
    movie_payload = load_json(ROOT / "public" / "data" / "movies_data.json")
    raw_movies = load_json(PIPELINE / "movies.json")
    index = load_json(PIPELINE / "movie_embedding_index.json")
    content = np.load(PIPELINE / "movie_embeddings.npy")
    keywords = np.load(PIPELINE / "movie_keyword_embeddings.npy")
    movies = movie_payload["movies"]

    print("MODEL AND NORMALIZATION")
    print({"python_model": index["model"], "normalized": index["normalized"], "shape": tuple(content.shape)})
    probe_model = SentenceTransformer(index["model"], local_files_only=True)
    probe = probe_model.encode(SAMPLE_SENTENCE, convert_to_numpy=True, normalize_embeddings=True)
    print({"sample": SAMPLE_SENTENCE, "magnitude": round(float(np.linalg.norm(probe)), 8), "first_8": [round(float(value), 8) for value in probe[:8]]})
    probe_output = PIPELINE / ".cache" / "python_embedding_probe.json"
    probe_output.parent.mkdir(exist_ok=True)
    with probe_output.open("w", encoding="utf-8") as file:
        json.dump({"sample": SAMPLE_SENTENCE, "vector": probe.astype(float).tolist()}, file)

    content_valid = np.isfinite(content).all(axis=1) & (np.linalg.norm(content, axis=1) > 0)
    keyword_valid = np.isfinite(keywords).all(axis=1) & (np.linalg.norm(keywords, axis=1) > 0)
    raw_by_id = {str(movie["tmdb_id"]): movie for movie in raw_movies}
    no_keyword_text = [movie for movie in movies if not raw_by_id[str(movie["id"])].get("keywords")]
    print("\nDATA INTEGRITY")
    missing_keyword_mask = np.asarray([not raw_by_id[str(movie["id"])].get("keywords") for movie in movies])
    sample_query_vector = probe_model.encode(SAMPLE_SENTENCE, convert_to_numpy=True, normalize_embeddings=True)
    fallback_scores = .70 * (content @ sample_query_vector) + .30 * (keywords @ sample_query_vector)
    fallback_scores[missing_keyword_mask] = (content @ sample_query_vector)[missing_keyword_mask]
    print({"movies": len(movies), "valid_content_embeddings": int(content_valid.sum()), "invalid_content_embeddings": int((~content_valid).sum()), "valid_keyword_embeddings": int(keyword_valid.sum()), "missing_keyword_embeddings": int((~keyword_valid).sum()), "movies_without_keywords": len(no_keyword_text), "content_only_fallback_verified": bool(np.allclose(fallback_scores[missing_keyword_mask], (content @ sample_query_vector)[missing_keyword_mask]))})

    # Baseline: this reproduces the currently deployed 70/30 scorer exactly.
    print("\nCURRENT HYBRID SCORE DISTRIBUTION (TOP 10)")
    all_top_scores = []
    for query in QUERIES:
        vector = probe_model.encode(query, convert_to_numpy=True, normalize_embeddings=True)
        content_scores = content @ vector
        keyword_scores = keywords @ vector
        hybrid_scores = .70 * content_scores + .30 * keyword_scores
        results = format_results(hybrid_scores, movies)
        all_top_scores.append(hybrid_scores.max())
        print(json.dumps({
            "query": query,
            "min": round(float(hybrid_scores.min()), 4),
            "mean": round(float(hybrid_scores.mean()), 4),
            "max": round(float(hybrid_scores.max()), 4),
            "top_10": results,
        }, ensure_ascii=False))
    print("\nBASELINE TOP-SCORE SUMMARY")
    print({"min": round(float(np.min(all_top_scores)), 4), "mean": round(float(np.mean(all_top_scores)), 4), "max": round(float(np.max(all_top_scores)), 4)})


if __name__ == "__main__":
    main()
