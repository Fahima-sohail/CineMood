"""Print the calibrated Python search results for the CineMood regression suite."""

from __future__ import annotations

import json

from sentence_transformers import SentenceTransformer

from semantic_search import load_search_assets, search_movies
from search_engine import load_config


QUERIES = [
    "a slow burn romance where they just talk all night",
    "getting over a breakup but making it cute",
    "falling in love with someone you're not supposed to",
    "a love story that breaks your heart at the end",
    "nothing is what it seems",
    "a twist I didn't see coming",
    "rich people behaving badly",
    "an unreliable narrator",
    "hopeful but kind of sad at the same time",
    "cozy but makes you cry",
    "big scale but still feels personal",
    "a dream within a dream kind of confusion",
    "something to watch when I'm sick and want to feel less alone",
    "a movie that makes prison feel hopeful somehow",
    "long distance relationship but make it space",
    "second chance love story",
    "a musical about time travel",
    "documentary about deep sea creatures",
]


def main() -> None:
    movies, content, keywords, index = load_search_assets()
    model = SentenceTransformer(index["model"], local_files_only=True)
    config = load_config()
    for query in QUERIES:
        rows, should_empty, expanded = search_movies(query, model, movies, content, keywords, config, limit=8)
        print(json.dumps({
            "query": query,
            "show_empty": should_empty,
            "expanded_query": expanded,
            "top_3": [{key: row[key] for key in ("title", "score", "confidence_label", "content_score", "keyword_score")} for row in rows[:3]],
        }, ensure_ascii=False))


if __name__ == "__main__":
    main()
