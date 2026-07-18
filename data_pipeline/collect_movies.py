"""Build CineMood's seed-guided movie dataset from TMDb's v3 API.

The corpus expands only through similar/recommended titles from the seed films,
keeping the first embedding dataset close to the viewer's actual taste.

Usage:
    python data_pipeline/collect_movies.py
    python data_pipeline/collect_movies.py --target 300 --delay 0.15
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
import time
from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable

import requests
from dotenv import load_dotenv


PROJECT_ROOT = Path(__file__).resolve().parents[1]
PIPELINE_DIR = Path(__file__).resolve().parent
OUTPUT_FILE = PIPELINE_DIR / "movies.json"
CACHE_DIR = PIPELINE_DIR / ".cache"
SEED_MATCH_CACHE = CACHE_DIR / "seed_matches.json"
CANDIDATE_POOL_CACHE = CACHE_DIR / "candidate_pool.json"
QUALITY_REJECTS_CACHE = CACHE_DIR / "quality_rejected_movie_ids.json"
API_ROOT = "https://api.themoviedb.org/3"
# These defaults deliberately favour well-known, well-received films. They can
# be relaxed through CLI arguments if a future seed pool cannot reach 250+.
DEFAULT_MIN_VOTE_AVERAGE = 6.5
DEFAULT_MIN_VOTE_COUNT = 300
REQUEST_TIMEOUT_SECONDS = 30


@dataclass(frozen=True)
class SeedMovie:
    """A deliberate title/year pair prevents incorrect matches for ambiguous names."""

    title: str
    year: int


# Exact requested seed titles, with release years for an auditable TMDb match.
SEEDS = [
    SeedMovie("La La Land", 2016), SeedMovie("Notting Hill", 1999),
    SeedMovie("How to Lose a Guy in 10 Days", 2003), SeedMovie("Through My Window", 2022),
    SeedMovie("Interstellar", 2014), SeedMovie("Inception", 2010),
    SeedMovie("The Shawshank Redemption", 1994), SeedMovie("Manchester by the Sea", 2016),
    SeedMovie("Purple Hearts", 2022), SeedMovie("Five Feet Apart", 2019),
    SeedMovie("Before Sunrise", 1995), SeedMovie("Before Sunset", 2004),
    SeedMovie("Before Midnight", 2013), SeedMovie("After", 2019),
    SeedMovie("After We Collided", 2020), SeedMovie("After We Fell", 2021),
    SeedMovie("After Ever Happy", 2022),
]

# Small, deliberate quality anchors fill emotional spaces that the romance/drama-
# heavy seed graph does not naturally reach (notably playful capers, family
# protection, animation, and high-stakes action). They are resolved exactly like
# seeds, quality-filtered, and do not replace the seed-guided expansion strategy.
COVERAGE_ANCHORS = [
    SeedMovie("Ocean's Eleven", 2001),
    SeedMovie("Baby Driver", 2017),
    SeedMovie("Logan Lucky", 2017),
    SeedMovie("Knives Out", 2019),
    SeedMovie("The Dark Knight", 2008),
    SeedMovie("Prisoners", 2013),
    SeedMovie("The Pursuit of Happyness", 2006),
    SeedMovie("Spirited Away", 2001),
    SeedMovie("Mad Max: Fury Road", 2015),
    SeedMovie("The Grand Budapest Hotel", 2014),
    # Twist, perception, and coming-of-age coverage anchors. Inception and
    # Catch Me If You Can are already in the seed-expanded corpus.
    SeedMovie("Fight Club", 1999),
    SeedMovie("Parasite", 2019),
    SeedMovie("The Sixth Sense", 1999),
    SeedMovie("Shutter Island", 2010),
    SeedMovie("Gone Girl", 2014),
    SeedMovie("10 Things I Hate About You", 1999),
    SeedMovie("The Truman Show", 1998),
    SeedMovie("Good Will Hunting", 1997),
    SeedMovie("Dead Poets Society", 1989),
    SeedMovie("The Perks of Being a Wallflower", 2012),
    SeedMovie("Titanic", 1997),
    SeedMovie("Mr. & Mrs. Smith", 2005),
    SeedMovie("Memento", 2000),
    SeedMovie("12 Angry Men", 1957),
]


def load_json(path: Path, default: Any) -> Any:
    """Read a cache safely; an interrupted/invalid cache never blocks a rerun."""
    if not path.exists():
        return default
    try:
        with path.open("r", encoding="utf-8") as file:
            return json.load(file)
    except (OSError, json.JSONDecodeError):
        print(f"Warning: ignoring unreadable cache at {path}")
        return default


def write_json(path: Path, payload: Any) -> None:
    """Atomically write JSON so Ctrl+C cannot leave a broken resume file."""
    path.parent.mkdir(parents=True, exist_ok=True)
    # A process-specific temporary name avoids collisions after an interrupted
    # collection run is still unwinding in another terminal.
    temporary = path.with_name(f"{path.name}.{os.getpid()}.tmp")
    with temporary.open("w", encoding="utf-8") as file:
        json.dump(payload, file, indent=2, ensure_ascii=False)
        file.write("\n")
    for attempt in range(5):
        try:
            temporary.replace(path)
            return
        except PermissionError:
            if attempt == 4:
                raise
            time.sleep(.25 * (attempt + 1))


def normalize_title(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "", value.lower())


def year_from_date(value: str | None) -> int | None:
    try:
        return int(value[:4]) if value and len(value) >= 4 else None
    except ValueError:
        return None


def clean_text(value: str | None, limit: int | None = None) -> str:
    cleaned = re.sub(r"\s+", " ", value or "").strip()
    return f"{cleaned[:limit].rstrip()}…" if limit and len(cleaned) > limit else cleaned


def console_safe(value: Any) -> str:
    """Avoid losing a long collection run to a legacy Windows console codec."""
    text = str(value)
    encoding = sys.stdout.encoding or "utf-8"
    return text.encode(encoding, errors="replace").decode(encoding, errors="replace")


class TMDbClient:
    """Paced, retried client for this collection job."""

    def __init__(self, api_key: str, delay: float) -> None:
        self.session = requests.Session()
        self.api_key = api_key
        self.delay = delay
        self.last_request_at = 0.0

    def get(self, endpoint: str, **params: Any) -> dict[str, Any]:
        """Call TMDb v3 and retry temporary/429 failures with backoff."""
        payload = {"api_key": self.api_key, "language": "en-US", **params}
        for attempt in range(4):
            wait = self.delay - (time.monotonic() - self.last_request_at)
            if wait > 0:
                time.sleep(wait)
            try:
                response = self.session.get(f"{API_ROOT}{endpoint}", params=payload, timeout=REQUEST_TIMEOUT_SECONDS)
                self.last_request_at = time.monotonic()
            except requests.RequestException as error:
                if attempt == 3:
                    raise RuntimeError(f"Network error for {endpoint}: {error}") from error
                time.sleep(1.5 * (attempt + 1))
                continue
            if response.status_code == 429 or response.status_code >= 500:
                if attempt == 3:
                    response.raise_for_status()
                retry_after = float(response.headers.get("Retry-After", 0) or 0)
                time.sleep(max(retry_after, 1.5 * (attempt + 1)))
                continue
            if response.status_code == 404:
                return {}
            response.raise_for_status()
            return response.json()
        return {}


def resolver_score(candidate: dict[str, Any], seed: SeedMovie) -> tuple[int, int, int]:
    """Rank exact normalized title/year matches ahead of popularity fallbacks."""
    title = candidate.get("title") or candidate.get("original_title") or ""
    release_year = year_from_date(candidate.get("release_date"))
    exact_title = int(normalize_title(title) == normalize_title(seed.title))
    exact_year = int(release_year == seed.year)
    close_year = max(0, 4 - abs((release_year or 0) - seed.year))
    return (exact_title * 100 + exact_year * 30 + close_year, int(candidate.get("vote_count") or 0), int(candidate.get("popularity") or 0))


def resolve_seed(client: TMDbClient, seed: SeedMovie) -> dict[str, Any] | None:
    """Search with year first, then title-only as a TMDb regional-release fallback."""
    results = client.get("/search/movie", query=seed.title, year=seed.year, include_adult="false").get("results", [])
    if not results:
        results = client.get("/search/movie", query=seed.title, include_adult="false").get("results", [])
    return max(results, key=lambda item: resolver_score(item, seed)) if results else None


def resolve_seeds(client: TMDbClient) -> tuple[list[dict[str, Any]], list[str]]:
    cached = load_json(SEED_MATCH_CACHE, {})
    resolved, failures = [], []
    for seed in SEEDS:
        key = f"{seed.title}|{seed.year}"
        match = cached.get(key) or resolve_seed(client, seed)
        if match:
            cached[key] = match
            write_json(SEED_MATCH_CACHE, cached)
            matched_year = year_from_date(match.get("release_date")) or "unknown year"
            print(console_safe(f"SEED MATCH: {seed.title} ({seed.year}) -> {match.get('title')} ({matched_year}) [TMDb {match['id']} ]"))
            resolved.append({"seed": seed.title, "id": int(match["id"])})
        else:
            print(f"SEED FAILED: {seed.title} ({seed.year})")
            failures.append(seed.title)
    return resolved, failures


def resolve_coverage_anchors(client: TMDbClient) -> list[dict[str, Any]]:
    """Resolve the compact, documented diversity anchors without expanding from them."""
    cached = load_json(SEED_MATCH_CACHE, {})
    resolved: list[dict[str, Any]] = []
    for anchor in COVERAGE_ANCHORS:
        key = f"anchor|{anchor.title}|{anchor.year}"
        match = cached.get(key) or resolve_seed(client, anchor)
        if not match:
            print(f"ANCHOR FAILED: {anchor.title} ({anchor.year})")
            continue
        cached[key] = match
        write_json(SEED_MATCH_CACHE, cached)
        print(console_safe(f"ANCHOR MATCH: {anchor.title} ({anchor.year}) -> {match.get('title')} [TMDb {match['id']} ]"))
        resolved.append({"seed": anchor.title, "id": int(match["id"])})
    return resolved


def collect_candidate_pool(client: TMDbClient, resolved_seeds: Iterable[dict[str, Any]], pages: int) -> dict[str, dict[str, Any]]:
    """Cache only IDs/titles/sources here; full details remain deferred."""
    pool = load_json(CANDIDATE_POOL_CACHE, {})
    for seed in resolved_seeds:
        for endpoint in ("similar", "recommendations"):
            for page in range(1, pages + 1):
                for result in client.get(f"/movie/{seed['id']}/{endpoint}", page=page).get("results", []):
                    if not result.get("id"):
                        continue
                    key = str(result["id"])
                    source = {"seed": seed["seed"], "endpoint": endpoint}
                    if key not in pool:
                        pool[key] = {"id": int(result["id"]), "title": result.get("title") or result.get("original_title") or "Untitled", "year": year_from_date(result.get("release_date")), "sources": [source]}
                    elif source not in pool[key].setdefault("sources", []):
                        pool[key]["sources"].append(source)
                write_json(CANDIDATE_POOL_CACHE, pool)
    return pool


def diverse_candidate_order(pool: dict[str, dict[str, Any]], seed_ids: set[int]) -> list[int]:
    """Round-robin seed neighborhoods to retain broad moods, then use shared titles."""
    by_seed: dict[str, list[int]] = defaultdict(list)
    for candidate in pool.values():
        movie_id = int(candidate["id"])
        if movie_id not in seed_ids:
            for source in candidate.get("sources", []):
                by_seed[source["seed"]].append(movie_id)
    queue, seen = [], set()
    positions = defaultdict(int)
    while True:
        added = False
        for seed in SEEDS:
            candidates = by_seed[seed.title]
            while positions[seed.title] < len(candidates) and candidates[positions[seed.title]] in seen:
                positions[seed.title] += 1
            if positions[seed.title] < len(candidates):
                movie_id = candidates[positions[seed.title]]
                positions[seed.title] += 1
                seen.add(movie_id)
                queue.append(movie_id)
                added = True
        if not added:
            break
    remaining = sorted((item for item in pool.values() if int(item["id"]) not in seen and int(item["id"]) not in seed_ids), key=lambda item: (-len(item.get("sources", [])), item.get("title", "")))
    return queue + [int(item["id"]) for item in remaining]


def format_reviews(client: TMDbClient, movie_id: int) -> list[dict[str, str | float | None]]:
    reviews = client.get(f"/movie/{movie_id}/reviews", page=1).get("results", [])
    reviews.sort(key=lambda review: (review.get("author_details", {}).get("rating") or 0, review.get("created_at") or ""), reverse=True)
    return [{"author": review.get("author", "TMDb user"), "rating": review.get("author_details", {}).get("rating"), "content": clean_text(review.get("content"), limit=1200)} for review in reviews[:5] if clean_text(review.get("content"))]


def fetch_keywords(client: TMDbClient, movie_id: int) -> list[str]:
    """Fetch TMDb's spoiler-light editorial keyword vocabulary for hybrid search."""
    response = client.get(f"/movie/{movie_id}/keywords")
    return [clean_text(keyword.get("name")) for keyword in response.get("keywords", []) if clean_text(keyword.get("name"))]


def meets_quality_threshold(movie: dict[str, Any], min_vote_average: float, min_vote_count: int) -> bool:
    """Use the same visible TMDb rating data for old and newly fetched records."""
    return float(movie.get("vote_average") or 0) >= min_vote_average and int(movie.get("vote_count") or 0) >= min_vote_count


def build_movie_record(
    client: TMDbClient,
    movie_id: int,
    is_seed: bool,
    min_vote_average: float,
    min_vote_count: int,
) -> dict[str, Any] | None:
    details = client.get(f"/movie/{movie_id}")
    if not details or not details.get("id") or not meets_quality_threshold(details, min_vote_average, min_vote_count):
        return None
    reviews = format_reviews(client, movie_id)
    overview = clean_text(details.get("overview"))
    return {"tmdb_id": int(details["id"]), "title": details.get("title") or details.get("original_title") or "Untitled", "year": year_from_date(details.get("release_date")), "genres": [genre["name"] for genre in details.get("genres", []) if genre.get("name")], "runtime": details.get("runtime"), "overview": overview, "poster_path": details.get("poster_path"), "vote_average": details.get("vote_average"), "vote_count": details.get("vote_count"), "keywords": fetch_keywords(client, movie_id), "reviews": reviews, "combined_text": "\n\n".join(part for part in [overview, *(review["content"] for review in reviews)] if part), "is_seed": is_seed, "collected_at": datetime.now(timezone.utc).isoformat()}


def refresh_keywords(client: TMDbClient, movies_by_id: dict[int, dict[str, Any]]) -> None:
    """Backfill old records once, then reuse the persisted keyword list on reruns."""
    missing = [movie for movie in movies_by_id.values() if "keywords" not in movie]
    if not missing:
        return
    print(f"Fetching TMDb keywords for {len(missing)} existing movie record(s)…")
    for index, movie in enumerate(missing, start=1):
        movie["keywords"] = fetch_keywords(client, int(movie["tmdb_id"]))
        write_json(OUTPUT_FILE, list(movies_by_id.values()))
        print(console_safe(f"Keywords {index:03d}/{len(missing)}: {movie['title']}"))


def print_summary(movies: list[dict[str, Any]], failed_seeds: list[str]) -> None:
    print("\n" + "=" * 72)
    average_rating = sum(float(movie.get("vote_average") or 0) for movie in movies) / len(movies) if movies else 0
    print(f"Collection complete: {len(movies)} movies saved to {OUTPUT_FILE}")
    print(f"Average TMDb rating: {average_rating:.2f} / 10")
    print(f"Seed titles that failed to resolve: {', '.join(failed_seeds) if failed_seeds else 'none'}")
    print("\nExample records:")
    for movie in movies[:3]:
        text = movie["combined_text"]
        print(console_safe(f"- {movie['title']} ({movie['year']}) | {movie['genres']} | {movie['vote_average']} rating from {movie['vote_count']} votes"))
        print(console_safe(f"  {text[:180]}{'…' if len(text) > 180 else ''}"))


def main() -> int:
    parser = argparse.ArgumentParser(description="Collect CineMood's seed-guided TMDb movie dataset.")
    parser.add_argument("--target", type=int, default=324, help="Maximum movies to save (default: 324).")
    parser.add_argument("--delay", type=float, default=0.12, help="Minimum seconds between TMDb calls (default: 0.12).")
    parser.add_argument("--candidate-pages", type=int, default=2, help="Pages from each similar/recommendations endpoint (default: 2).")
    parser.add_argument("--min-vote-average", type=float, default=DEFAULT_MIN_VOTE_AVERAGE, help="Minimum TMDb rating for every record (default: 6.5).")
    parser.add_argument("--min-vote-count", type=int, default=DEFAULT_MIN_VOTE_COUNT, help="Minimum TMDb vote count for every record (default: 300).")
    args = parser.parse_args()
    load_dotenv(PROJECT_ROOT / ".env")
    api_key = os.getenv("TMDB_API_KEY")
    if not api_key:
        print("TMDB_API_KEY is missing. Add it to a .env file in the project root.", file=sys.stderr)
        return 2

    client = TMDbClient(api_key, delay=args.delay)
    existing_movies = load_json(OUTPUT_FILE, [])
    quality_movies = [movie for movie in existing_movies if meets_quality_threshold(movie, args.min_vote_average, args.min_vote_count)]
    removed_count = len(existing_movies) - len(quality_movies)
    if removed_count:
        print(f"Removed {removed_count} existing record(s) below the {args.min_vote_average} rating / {args.min_vote_count} vote quality floor.")
    saved_by_id = {int(movie["tmdb_id"]): movie for movie in quality_movies if movie.get("tmdb_id")}
    rejected_candidate_ids = {int(movie_id) for movie_id in load_json(QUALITY_REJECTS_CACHE, [])}
    resolved_seeds, failed_seeds = resolve_seeds(client)
    resolved_anchors = resolve_coverage_anchors(client)
    seed_ids = {seed["id"] for seed in resolved_seeds}
    ordered_ids = [(seed["id"], True) for seed in resolved_seeds]
    ordered_ids.extend((anchor["id"], True) for anchor in resolved_anchors)
    pool = collect_candidate_pool(client, resolved_seeds, pages=args.candidate_pages)
    ordered_ids.extend((movie_id, False) for movie_id in diverse_candidate_order(pool, seed_ids))
    for movie_id, is_seed in ordered_ids:
        if len(saved_by_id) >= args.target:
            break
        if movie_id in saved_by_id:
            continue
        if not is_seed and movie_id in rejected_candidate_ids:
            continue
        try:
            record = build_movie_record(client, movie_id, is_seed, args.min_vote_average, args.min_vote_count)
        except (requests.RequestException, RuntimeError) as error:
            print(f"Skipping TMDb {movie_id}: {error}")
            continue
        if not record:
            if not is_seed:
                rejected_candidate_ids.add(movie_id)
                write_json(QUALITY_REJECTS_CACHE, sorted(rejected_candidate_ids))
            continue
        saved_by_id[movie_id] = record
        write_json(OUTPUT_FILE, list(saved_by_id.values()))
        print(console_safe(f"Saved {len(saved_by_id):03d}/{args.target}: {record['title']} ({record['year']})"))
    movies = list(saved_by_id.values())[:args.target]
    write_json(OUTPUT_FILE, movies)
    refresh_keywords(client, saved_by_id)
    movies = list(saved_by_id.values())[:args.target]
    write_json(OUTPUT_FILE, movies)
    print_summary(movies, failed_seeds)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
