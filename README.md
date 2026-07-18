# CineMood

CineMood is a static, mood-first movie discovery experience. Describe a feeling or scene in natural language, get semantically matched films, then explore each film's emotional journey.

## How it works

1. The offline pipeline collects a curated TMDb dataset with plot text, audience reviews, and keywords.
2. `all-MiniLM-L6-v2` generates normalized content and keyword embeddings for every movie.
3. In the browser, the same MiniLM model embeds the query and ranks films with a hybrid score: **70% content similarity + 30% keyword similarity**.
4. Emotional timelines use subtitle-derived sentiment curves for flagship films. Other films display a clearly labeled estimated arc derived from available text.

There is no runtime backend and no TMDb key in the browser. The site fetches only its checked-in static data files and runs query embedding and scoring locally, making it suitable for GitHub Pages.

## Run locally

Prerequisites: Node.js 20+ and npm.

```bash
npm install
npm run dev
```

Open the localhost URL Vite prints. The first search downloads the MiniLM model once; the browser cache is reused on later searches.

To create a production build:

```bash
npm run build
npm run preview
```

## Refresh static app data

After changing the pipeline dataset, embeddings, or tension curves, run:

```bash
python data_pipeline/export_static_app_data.py
```

This creates the deployable files in `public/data/`:

- `movies_data.json` — movie metadata plus content and keyword vectors
- `tension_curves.json` — subtitle-derived or estimated emotional timeline points

## Deploy to GitHub Pages

The workflow at `.github/workflows/deploy-pages.yml` builds and deploys on every push to `main`. In the GitHub repository, set **Settings → Pages → Build and deployment → Source** to **GitHub Actions**, then push the project to `main`.

The workflow passes the repository name to Vite so project-site asset paths work correctly. For example, a repository named `CineMood` deploys at `https://<your-user>.github.io/CineMood/`.
