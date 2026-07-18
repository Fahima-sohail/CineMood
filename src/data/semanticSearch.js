const DATA_URL = `${import.meta.env.BASE_URL}data/movies_data.json`
const TMDB_IMAGE_BASE = 'https://image.tmdb.org/t/p/w500'
const MODEL_ID = 'Xenova/all-MiniLM-L6-v2'

let datasetPromise
let extractorPromise
let transformersPromise

function loadTransformersRuntime() {
  if (!transformersPromise) {
    transformersPromise = import('@xenova/transformers').then(({ env, pipeline }) => {
      // Transformers.js stores downloaded model files in the browser cache.
      env.allowLocalModels = false
      env.useBrowserCache = true
      return pipeline
    })
  }
  return transformersPromise
}

function loadDataset() {
  if (!datasetPromise) {
    datasetPromise = fetch(DATA_URL)
      .then((response) => {
        if (!response.ok) throw new Error(`Could not load static movie data (${response.status}).`)
        return response.json()
      })
      .then((payload) => {
        if (!payload.normalized || !Array.isArray(payload.movies)) throw new Error('Movie data is malformed or not normalized.')
        return payload
      })
  }
  return datasetPromise
}

function loadExtractor(onProgress) {
  if (!extractorPromise) {
    extractorPromise = loadTransformersRuntime().then((pipeline) => pipeline('feature-extraction', MODEL_ID, {
      progress_callback: (event) => onProgress?.({ phase: 'model', event }),
    }))
  }
  return extractorPromise
}

function formatRuntime(minutes) {
  if (!minutes) return 'Runtime unavailable'
  return `${Math.floor(minutes / 60)}h ${minutes % 60}m`
}

function curveForId(id) {
  let state = Number(id) || 1
  const random = () => { state = (state * 1664525 + 1013904223) % 4294967296; return state / 4294967296 }
  let tension = 22 + random() * 22
  return Array.from({ length: 16 }, (_, index) => {
    tension += (random() - .4) * 22 + index * .55
    tension = Math.max(13, Math.min(94, tension))
    return Math.round(tension)
  })
}

function confidenceFromScore(score) {
  // Calibrated from the offline MiniLM validation: strong ≈ .45-.53, looser ≈ .27-.30.
  const percentage = Math.round(Math.max(35, Math.min(98, 32 + (score - .15) * 160)))
  if (score >= .45) return { percentage, label: 'Exceptional match' }
  if (score >= .36) return { percentage, label: 'Strong match' }
  if (score >= .28) return { percentage, label: 'Moderate match' }
  return { percentage, label: 'Possible match' }
}

function decorateMovie(movie, score) {
  const confidence = confidenceFromScore(score)
  const genres = movie.genres?.length ? movie.genres : ['Unclassified']
  return {
    id: String(movie.id),
    tmdbId: movie.id,
    title: movie.title,
    year: String(movie.year || '—'),
    duration: formatRuntime(movie.runtime),
    mood: genres.slice(0, 2).join(' • '),
    summary: movie.overview || 'TMDb does not currently provide an overview for this title.',
    poster: movie.poster_path ? `${TMDB_IMAGE_BASE}${movie.poster_path}` : `https://placehold.co/700x1000/16181D/F2F0EC?text=${encodeURIComponent(movie.title)}`,
    voteAverage: movie.vote_average,
    voteCount: movie.vote_count,
    genres,
    similarity: score,
    match: confidence.percentage,
    confidenceLabel: confidence.label,
    reason: `Semantic similarity of ${score.toFixed(3)} across the film’s synopsis and audience response.`,
    matchReasons: [`${confidence.label}`, `${movie.vote_average?.toFixed?.(1) ?? movie.vote_average}/10 TMDb rating`, genres.slice(0, 2).join(' + ')],
    // The actual sentiment classifier has not been built. This deterministic
    // curve preserves the UI while explicitly remaining a placeholder.
    curve: curveForId(movie.id),
  }
}

function dotProduct(left, right) {
  let score = 0
  for (let index = 0; index < left.length; index += 1) score += left[index] * right[index]
  return score
}

/** Embed a query locally and rank the static corpus with cosine similarity. */
export async function searchMovies(query, { limit = 8, onProgress } = {}) {
  onProgress?.({ phase: 'data' })
  const [dataset, extractor] = await Promise.all([loadDataset(), loadExtractor(onProgress)])
  onProgress?.({ phase: 'embedding' })
  const output = await extractor(query, { pooling: 'mean', normalize: true })
  const queryVector = output.data
  onProgress?.({ phase: 'comparing' })
  const scored = dataset.movies.map((movie) => ({ movie, score: dotProduct(movie.embedding, queryVector) }))
  scored.sort((left, right) => right.score - left.score)
  onProgress?.({ phase: 'ranking' })
  return scored.slice(0, limit).map(({ movie, score }) => decorateMovie(movie, score))
}
