# CineMood data pipeline — collection step

This folder contains the TMDb collection step and a local semantic-search test harness. The collector resolves the curated titles in `collect_movies.py`, expands through each seed's **similar** and **recommendations** endpoints, then collects full metadata only for the selected ~300 records.

## Setup

Create `.env` in the project root:

```env
TMDB_API_KEY=your_tmdb_v3_api_key
```

Install and run from the project root:

```powershell
py -m venv .venv --system-site-packages
.\.venv\Scripts\python.exe -m pip install -r data_pipeline/requirements.txt
.\.venv\Scripts\python.exe data_pipeline/collect_movies.py
```

Options:

```powershell
.\.venv\Scripts\python.exe data_pipeline/collect_movies.py --target 20
.\.venv\Scripts\python.exe data_pipeline/collect_movies.py --delay 0.25
```

Quality defaults are a TMDb rating of **6.5+** and **300+ votes** for every saved film. Existing output is pruned on rerun, and the same rule applies to newly expanded candidates. Adjust only if the collection falls below the desired 250–350 range:

```powershell
.\.venv\Scripts\python.exe data_pipeline/collect_movies.py --min-vote-average 6.3 --min-vote-count 250
```

## Outputs and resuming

- `movies.json`: clean movie records for the embedding step.
- `.cache/seed_matches.json`: chosen TMDb IDs, useful for auditing ambiguous titles.
- `.cache/candidate_pool.json`: candidate IDs/titles with their seed/source links.

The script writes after every full movie record. Rerunning it reuses caches and saved movies rather than fetching them again. Candidate selection is round-robin across seed neighborhoods so the corpus retains broad emotional coverage while remaining taste-guided.

## Build and test semantic search

After collection, install the dependencies and generate local embeddings. The `all-MiniLM-L6-v2` model downloads once from Hugging Face and then runs locally.

```powershell
.\.venv\Scripts\python.exe data_pipeline/build_embeddings.py
.\.venv\Scripts\python.exe data_pipeline/semantic_search.py
```

The build writes `movie_embeddings.npy` (normalized float vectors) and `movie_embedding_index.json` (the matching TMDb ID row order). The search command runs the four requested sanity-check queries, prints the top five movies for each, and reports per-query plus combined similarity-score distributions.

## Export static frontend data

After rebuilding embeddings, produce the browser-ready static dataset. This embeds no secrets and is the only data file the GitHub Pages frontend needs at runtime:

```powershell
.\.venv\Scripts\python.exe data_pipeline/export_frontend_data.py
```

It creates `public/data/movies_data.json`, containing each movie's display metadata and its normalized MiniLM vector.

Run a single ad-hoc query with:

```powershell
.\.venv\Scripts\python.exe data_pipeline/semantic_search.py --query "a love story that feels like a long conversation" --limit 10
```

Hybrid search uses 70% `combined_text` similarity and 30% TMDb-keyword similarity. Adjust `CONTENT_WEIGHT` and `KEYWORD_WEIGHT` at the top of `semantic_search.py`, then rerun the validation suite to compare content and hybrid scores side-by-side.

## Tension-curve pipeline

The curve pipeline is intentionally separate from collection/search. Add this to `.env` before subtitle collection:

```env
OPENSUBS_API_KEY=your_opensubtitles_api_key
```

Then run the stages in order:

```powershell
.\.venv\Scripts\python.exe data_pipeline/train_tone_classifier.py
.\.venv\Scripts\python.exe data_pipeline/download_flagship_subtitles.py
.\.venv\Scripts\python.exe data_pipeline/build_tension_curves.py
```

`flagship_movies.py` defines the 15 subtitle-backed titles. `tension_curves.json` labels each curve with `is_approximate`: `false` for successful subtitle-derived curves and `true` for review-text estimates (including any flagship whose subtitle could not be retrieved).
