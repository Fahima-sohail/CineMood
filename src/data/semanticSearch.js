import { expandQuery, rankMovieMatches } from './searchRanking'

const DATA_URL = `${import.meta.env.BASE_URL}data/movies_data.json`
const CURVES_URL = `${import.meta.env.BASE_URL}data/tension_curves.json`
const SEARCH_CONFIG_URL = `${import.meta.env.BASE_URL}data/search_config.json`
const TMDB_IMAGE_BASE = 'https://image.tmdb.org/t/p/w500'
const MODEL_ID = 'Xenova/all-MiniLM-L6-v2'

let datasetPromise
let curvesPromise
let configPromise
let extractorPromise
let transformersPromise

function loadTransformersRuntime() {
  if (!transformersPromise) {
    transformersPromise = import('@xenova/transformers').then(({ env, pipeline }) => {
      env.allowLocalModels = false
      env.useBrowserCache = true
      return pipeline
    })
  }
  return transformersPromise
}

function loadJson(url, errorMessage) {
  return fetch(url).then((response) => {
    if (!response.ok) throw new Error(`${errorMessage} (${response.status}).`)
    return response.json()
  })
}

function loadDataset() {
  if (!datasetPromise) {
    datasetPromise = loadJson(DATA_URL, 'Could not load static movie data').then((payload) => {
      if (!payload.normalized || !Array.isArray(payload.movies)) throw new Error('Movie data is malformed or not normalized.')
      return payload
    })
  }
  return datasetPromise
}

function loadCurves() {
  if (!curvesPromise) curvesPromise = loadJson(CURVES_URL, 'Could not load emotional timelines')
  return curvesPromise
}

function loadSearchConfig() {
  if (!configPromise) configPromise = loadJson(SEARCH_CONFIG_URL, 'Could not load search calibration')
  return configPromise
}

function loadExtractor(onProgress) {
  if (!extractorPromise) {
    extractorPromise = loadTransformersRuntime().then((pipeline) => pipeline('feature-extraction', MODEL_ID, {
      // Match SentenceTransformer's fp32 output; the default quantized model drifted from the offline index.
      quantized: false,
      progress_callback: (event) => onProgress?.({ phase: 'model', event }),
    }))
  }
  return extractorPromise
}

function formatRuntime(minutes) {
  if (!minutes) return 'Runtime unavailable'
  return `${Math.floor(minutes / 60)}h ${minutes % 60}m`
}

function decorateMovie(movie, result, curveData, shouldShowEmpty) {
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
    similarity: result.score,
    contentSimilarity: result.contentScore,
    keywordSimilarity: result.keywordScore,
    match: result.confidence.percentage,
    confidenceLabel: result.confidence.label,
    shouldShowEmpty,
    reason: `Hybrid similarity ${result.score.toFixed(3)}: semantic story cues plus TMDb keywords.`,
    matchReasons: [result.confidence.label, `${movie.vote_average?.toFixed?.(1) ?? movie.vote_average}/10 TMDb rating`, genres.slice(0, 2).join(' + ')],
    tensionCurve: curveData,
    isApproximate: curveData?.is_approximate ?? true,
    curve: curveData?.points?.map((point) => point.mood_score) ?? [30, 38, 48, 57, 45, 62, 54, 40],
  }
}

/** Embed one locally expanded query, then rank the static corpus with the offline-calibrated hybrid scorer. */
export async function searchMovies(query, { limit = 8, onProgress } = {}) {
  onProgress?.({ phase: 'data' })
  const [dataset, curves, config, extractor] = await Promise.all([loadDataset(), loadCurves(), loadSearchConfig(), loadExtractor(onProgress)])
  onProgress?.({ phase: 'embedding' })
  const output = await extractor(expandQuery(query, config), { pooling: 'mean', normalize: true })
  onProgress?.({ phase: 'comparing' })
  const ranked = rankMovieMatches(query, output.data, dataset.movies, config, limit)
  onProgress?.({ phase: 'ranking' })
  return ranked.matches.map((result) => decorateMovie(result.movie, result, curves[String(result.movie.id)], ranked.isEmpty))
}
