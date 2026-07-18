"""Train a compact calm/happy/sad/tense classifier from GoEmotions.

This is a coarse affect proxy, not a claim about a film's definitive emotion.
"""
from __future__ import annotations

from pathlib import Path

import joblib
from datasets import load_dataset
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import Pipeline

PIPELINE = Path(__file__).resolve().parent
OUTPUT = PIPELINE / "tone_classifier.joblib"
# GoEmotions simplified label IDs: neutral=27, joy=17, love=18, fear=14, etc.
LABEL_TO_TONE = {
    0: "happy", 1: "happy", 4: "happy", 5: "happy", 8: "happy", 13: "happy", 15: "happy", 17: "happy", 18: "happy", 20: "happy", 21: "happy", 23: "happy",
    2: "tense", 3: "tense", 6: "tense", 10: "tense", 11: "tense", 12: "tense", 14: "tense", 19: "tense", 26: "tense",
    9: "sad", 16: "sad", 24: "sad", 25: "sad",
    7: "calm", 22: "calm", 27: "calm",
}


def flatten(split):
    texts, labels = [], []
    for row in split:
        mapped = [LABEL_TO_TONE[label] for label in row["labels"] if label in LABEL_TO_TONE]
        if not mapped:
            continue
        # Keep unambiguous examples for a stable, interpretable four-way model.
        if len(set(mapped)) == 1:
            texts.append(row["text"])
            labels.append(mapped[0])
    return texts, labels


def main() -> int:
    dataset = load_dataset("google-research-datasets/go_emotions", "simplified")
    train_texts, train_labels = flatten(dataset["train"])
    validation_texts, validation_labels = flatten(dataset["validation"])
    classifier = Pipeline([("tfidf", TfidfVectorizer(ngram_range=(1, 2), min_df=2, max_features=70000, sublinear_tf=True)), ("logreg", LogisticRegression(max_iter=1000, class_weight="balanced", n_jobs=-1))])
    classifier.fit(train_texts, train_labels)
    print(f"GoEmotions validation accuracy: {classifier.score(validation_texts, validation_labels):.3f}")
    joblib.dump(classifier, OUTPUT)
    print(f"Saved tone classifier to {OUTPUT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
