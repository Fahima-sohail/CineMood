"""Download one English .srt per flagship movie from OpenSubtitles.

Requires OPENSUBS_API_KEY in the project-root .env. Files are cached under
data_pipeline/.cache/subtitles so reruns do not consume duplicate downloads.
"""
from __future__ import annotations

import argparse
import gzip
import json
import os
import time
from pathlib import Path

import requests
from dotenv import load_dotenv

from flagship_movies import FLAGSHIP_TITLES

ROOT = Path(__file__).resolve().parents[1]
PIPELINE = Path(__file__).resolve().parent
SUBTITLE_DIR = PIPELINE / ".cache" / "subtitles"
MOVIES_PATH = PIPELINE / "movies.json"
API_ROOT = "https://api.opensubtitles.com/api/v1"
USER_AGENT = "CineMood v1.0"


def request(session: requests.Session, method: str, path: str, headers: dict, delay: float, **kwargs):
    response = session.request(method, f"{API_ROOT}{path}", headers=headers, timeout=30, **kwargs)
    time.sleep(delay)
    response.raise_for_status()
    return response


def main() -> int:
    parser = argparse.ArgumentParser(description="Download cached English flagship subtitles from OpenSubtitles.")
    parser.add_argument("--delay", type=float, default=1.1, help="Minimum pause after every API request.")
    args = parser.parse_args()
    load_dotenv(ROOT / ".env")
    api_key = os.getenv("OPENSUBS_API_KEY")
    if not api_key:
        print("OPENSUBS_API_KEY is missing; no subtitle requests were made.")
        return 2
    movies = json.loads(MOVIES_PATH.read_text(encoding="utf-8"))
    by_title = {movie["title"]: movie for movie in movies}
    headers = {"Api-Key": api_key, "User-Agent": USER_AGENT, "Content-Type": "application/json"}
    session = requests.Session()
    SUBTITLE_DIR.mkdir(parents=True, exist_ok=True)
    for title in FLAGSHIP_TITLES:
        movie = by_title.get(title)
        if not movie:
            print(f"SKIP missing dataset movie: {title}")
            continue
        output = SUBTITLE_DIR / f"{movie['tmdb_id']}.srt"
        if output.exists() and output.stat().st_size:
            print(f"CACHED: {title}")
            continue
        try:
            search = request(session, "GET", "/subtitles", headers, args.delay, params={"tmdb_id": movie["tmdb_id"], "languages": "en", "order_by": "download_count", "order_direction": "desc"}).json()
            candidates = search.get("data", [])
            if not candidates:
                print(f"UNAVAILABLE: {title}")
                continue
            file_id = candidates[0]["attributes"]["files"][0]["file_id"]
            download = request(session, "POST", "/download", headers, args.delay, json={"file_id": file_id}).json()
            content = session.get(download["link"], timeout=60).content
            if content[:2] == b"\x1f\x8b":
                content = gzip.decompress(content)
            output.write_bytes(content)
            print(f"DOWNLOADED: {title}")
        except (requests.RequestException, KeyError, IndexError, OSError) as error:
            print(f"FAILED {title}: {error}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
