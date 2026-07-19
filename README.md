# CineMood

**Describe a feeling. Discover films that match it. Explore the emotional journey.**

[Open CineMood](https://fahima-sohail.github.io/CineMood/) · [Report an issue](https://github.com/Fahima-sohail/CineMood/issues) · [View the repository](https://github.com/Fahima-sohail/CineMood)

CineMood is a mood-first movie discovery experience. Instead of starting with a title or genre, you can search in natural language—such as *“a quiet devastating ending”* or *“a slow-burn romance where they just talk all night”*—and receive films ranked by emotional and semantic similarity.

The app is completely static at runtime: no application server, database, or TMDb API key is exposed in the browser.


## What it does

- Searches a curated collection of **324 quality-filtered films** using natural-language meaning rather than title matching.
- Runs query embedding and ranking **locally in the browser**.
- Blends plot/review similarity with TMDb keyword similarity using a calibrated **70% content / 30% keyword** hybrid score.
- Shows confidence bands relative to the current result set instead of rejecting sensible prompts with a fixed score cutoff.
- Displays an emotional timeline for each film:
  - **15 subtitle-derived flagship curves**
  - **309 clearly labelled estimated arcs** for the remaining films

## Experience flow

```text
Describe a feeling → CineMood embeds its meaning → ranks films locally → explore a film’s emotional arc
```

## Search and ML approach

### Semantic retrieval

The dataset stores two L2-normalized, 384-dimensional vectors for every film:

1. **Content embedding** — the movie overview plus selected TMDb review text.
2. **Keyword embedding** — the film’s TMDb keywords.

Both the offline pipeline and browser use **`all-MiniLM-L6-v2`**. The browser uses the fp32 Transformers.js model to match the Python embeddings precisely, then computes cosine similarity with a simple dot product.

```text
hybrid score = 0.70 × content cosine similarity
             + 0.30 × keyword cosine similarity
```

Movies without TMDb keywords automatically fall back to content-only scoring, so they are not penalized by missing metadata. A small local intent vocabulary expands a few high-level concepts—such as plot twists, comfort viewing, or bittersweet endings—without naming or hardcoding movie titles.

### Confidence and empty states

CineMood always ranks the strongest available results. `High`, `Medium`, and `Low` confidence are calculated from score gaps inside the top result set, rather than from a global absolute cutoff.

The “no strong match” state is reserved for unsupported combined requests, for example a *musical about time travel* when the collection has films matching each individual idea but none that support both together.

### Emotional timelines

The emotion pipeline uses a four-tone proxy: `calm`, `happy`, `sad`, and `tense`.

- **Training data:** Google Research’s GoEmotions simplified dataset.
- **Classifier:** TF-IDF (unigrams + bigrams) followed by balanced multinomial logistic regression from scikit-learn.
- **Flagship films:** English OpenSubtitles `.srt` dialogue is grouped into runtime buckets, classified, and converted to timeline points.
- **Other films:** the available plot/review text is split into broad segments and marked as an **Estimated arc** in the interface.

These curves are an interpretable affect signal, not a claim that a film has one definitive emotional reading.

## Static architecture

```text
Offline Python pipeline                         Static GitHub Pages app
──────────────────────                         ───────────────────────
TMDb metadata + reviews + keywords   ───────→  public/data/movies_data.json
SentenceTransformers embeddings      ───────→  browser-side MiniLM query embedding
GoEmotions tone model + subtitles    ───────→  public/data/tension_curves.json
                                                local ranking + visual timelines
```

Why static?

- No runtime API secrets or backend infrastructure.
- Fast, low-cost GitHub Pages deployment.
- Search text stays in the visitor’s browser after the page loads.
- The MiniLM model is downloaded only on first use and cached by the browser for later searches.

Movie posters are loaded from TMDb’s public image CDN using poster paths collected during the offline pipeline. CineMood does not call TMDb’s API at runtime.

## Tech stack

- React 18 + Vite
- Tailwind CSS
- GSAP and Lenis for restrained motion and smooth scrolling
- `@xenova/transformers` for in-browser MiniLM embeddings
- Python, SentenceTransformers, NumPy, scikit-learn, Hugging Face Datasets
- TMDb API for offline metadata collection
- OpenSubtitles API for flagship subtitle acquisition

## Run locally

### Frontend

Prerequisites: Node.js 20+ and npm.

```bash
git clone https://github.com/Fahima-sohail/CineMood.git
cd CineMood
npm install
npm run dev
```

Open the localhost URL printed by Vite. On the first search, the fp32 MiniLM model downloads and is cached by the browser. Internet access is therefore needed once for the model and poster images.

Useful commands:

```bash
npm run lint
npm run build
npm run preview
```

### Optional: run the Python pipeline

Prerequisites: Python 3.10+ and a TMDb API key for collection. Add credentials to a root `.env` file:

```env
TMDB_API_KEY=your_tmdb_key
OPENSUBS_API_KEY=your_opensubtitles_key
```

Create an environment and install the pipeline dependencies:

```bash
python -m venv .venv
# Windows PowerShell
.\.venv\Scripts\Activate.ps1
pip install -r data_pipeline/requirements.txt
```

Common pipeline commands:

```bash
python data_pipeline/collect_movies.py
python data_pipeline/build_embeddings.py
python data_pipeline/train_tone_classifier.py
python data_pipeline/download_flagship_subtitles.py
python data_pipeline/build_tension_curves.py
python data_pipeline/export_static_app_data.py
```

## Search verification

The project includes reproducible correctness checks for model parity, data integrity, scoring, and frontend-ranking parity:

```bash
.\.venv\Scripts\python.exe data_pipeline/audit_search.py
.\.venv\Scripts\python.exe data_pipeline/run_search_regression.py
node data_pipeline/verify_transformers_embedding.mjs
node data_pipeline/verify_frontend_search.mjs
```

The embedding parity check confirms that Python SentenceTransformers and fp32 Transformers.js emit matching normalized vectors for the same text.

## Deploy to GitHub Pages

This repository includes a GitHub Actions deployment workflow at [`.github/workflows/deploy-pages.yml`](.github/workflows/deploy-pages.yml).

1. Push the project to the `main` branch.
2. On GitHub, open **Settings → Pages**.
3. Under **Build and deployment**, select **GitHub Actions** as the source.
4. Open the **Actions** tab and wait for **Deploy CineMood to GitHub Pages** to complete.
5. Visit **https://fahima-sohail.github.io/CineMood/**.

Every later push to `main` builds and deploys automatically. The workflow supplies Vite with the `/CineMood/` base path, so assets and static data resolve correctly on a GitHub project site.

## Project structure

```text
src/
  components/                 React UI components
  data/                       Browser search and ranking logic
public/data/
  movies_data.json            Movie metadata + content/keyword vectors
  tension_curves.json         Subtitle-derived and estimated arcs
  search_config.json          Shared scoring and intent-expansion settings
data_pipeline/
  collect_movies.py           TMDb collection and quality filtering
  build_embeddings.py         MiniLM content and keyword vectors
  train_tone_classifier.py    GoEmotions tone-classifier training
  build_tension_curves.py     Subtitle/review timeline generation
  export_static_app_data.py   Browser data export
.github/workflows/
  deploy-pages.yml            GitHub Pages deployment
```

## Data and attribution

This product uses the TMDb API endorsed by TMDb for personal use. Movie metadata, ratings, reviews, keywords, and poster paths originate from TMDb during the offline collection stage. Subtitle-derived data is collected from OpenSubtitles only for the designated flagship subset.


