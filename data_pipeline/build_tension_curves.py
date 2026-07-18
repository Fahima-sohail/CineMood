"""Create subtitle-verified flagship curves and review-text estimated curves."""
from __future__ import annotations

import json
import random
import re
from collections import defaultdict
from pathlib import Path

import joblib

from flagship_movies import FLAGSHIP_TITLES

PIPELINE = Path(__file__).resolve().parent
MOVIES_PATH = PIPELINE / "movies.json"
SUBTITLE_DIR = PIPELINE / ".cache" / "subtitles"
CLASSIFIER_PATH = PIPELINE / "tone_classifier.joblib"
OUTPUT_PATH = PIPELINE / "tension_curves.json"
SCORE_BY_TONE = {"calm": 20, "happy": 42, "sad": 64, "tense": 88}


def timestamp_seconds(value: str) -> float:
    hours, minutes, seconds = value.replace(",", ".").split(":")
    return int(hours) * 3600 + int(minutes) * 60 + float(seconds)


def parse_srt(path: Path):
    blocks = re.split(r"\r?\n\s*\r?\n", path.read_text(encoding="utf-8", errors="replace"))
    entries = []
    for block in blocks:
        lines = [line.strip() for line in block.splitlines() if line.strip()]
        timing = next((line for line in lines if "-->" in line), None)
        if not timing:
            continue
        try:
            start, end = [timestamp_seconds(part.strip()) for part in timing.split("-->")]
        except ValueError:
            continue
        text = " ".join(line for line in lines if line != timing and not line.isdigit())
        text = re.sub(r"<[^>]+>|\{[^}]+\}", "", text)
        if text:
            entries.append((start, end, text))
    return entries


def predict(classifier, text: str):
    probabilities = classifier.predict_proba([text])[0]
    labels = classifier.classes_
    dominant = labels[probabilities.argmax()]
    score = sum(float(probability) * SCORE_BY_TONE[label] for label, probability in zip(labels, probabilities))
    return round(score, 2), dominant


def subtitle_curve(classifier, movie, path: Path, buckets: int = 24):
    entries = parse_srt(path)
    if not entries:
        return None
    duration = (movie.get("runtime") or 0) * 60 or max(end for _, end, _ in entries)
    groups = defaultdict(list)
    for start, _, text in entries:
        index = min(buckets - 1, int((start / duration) * buckets))
        groups[index].append(text)
    return [{"time_percent": round((index + .5) / buckets * 100, 2), "mood_score": predict(classifier, " ".join(groups[index]))[0] if groups[index] else 20, "dominant_label": predict(classifier, " ".join(groups[index]))[1] if groups[index] else "calm"} for index in range(buckets)]


def approximate_curve(classifier, movie, points: int = 5):
    words = (movie.get("combined_text") or movie.get("overview") or "").split()
    chunk = max(1, len(words) // points)
    curve = []
    for index in range(points):
        text = " ".join(words[index * chunk:(index + 1) * chunk]) or movie.get("overview", "")
        score, label = predict(classifier, text)
        curve.append({"time_percent": round((index + .5) / points * 100, 2), "mood_score": score, "dominant_label": label})
    return curve


def main() -> int:
    movies = json.loads(MOVIES_PATH.read_text(encoding="utf-8"))
    classifier = joblib.load(CLASSIFIER_PATH)
    flagship = set(FLAGSHIP_TITLES)
    curves = {}
    for movie in movies:
        subtitle_path = SUBTITLE_DIR / f"{movie['tmdb_id']}.srt"
        if movie["title"] in flagship and subtitle_path.exists():
            curve = subtitle_curve(classifier, movie, subtitle_path)
            if curve:
                curves[str(movie["tmdb_id"])] = {"title": movie["title"], "is_approximate": False, "source": "opensubtitles", "points": curve}
                continue
        curves[str(movie["tmdb_id"])] = {"title": movie["title"], "is_approximate": True, "source": "review_text_estimate", "points": approximate_curve(classifier, movie)}
    OUTPUT_PATH.write_text(json.dumps(curves, indent=2), encoding="utf-8")
    print(f"Saved {len(curves)} tension curves to {OUTPUT_PATH}")
    samples = ["Before Sunrise", "Manchester by the Sea"] + [movie["title"] for movie in random.sample([movie for movie in movies if movie["title"] not in flagship], 2)]
    for title in samples:
        entry = next(value for value in curves.values() if value["title"] == title)
        print(f"\n{title} ({'estimated' if entry['is_approximate'] else 'subtitle-verified'}): {entry['points'][:3]} …")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
