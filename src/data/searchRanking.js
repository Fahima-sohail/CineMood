const STOP_WORDS = new Set(['a', 'an', 'the', 'about', 'and', 'of', 'in', 'on', 'to', 'with', 'for', 'from', 'that', 'this', 'it', 'is', 'are', 'make'])
const STRUCTURED_QUERY = /^(?:(?:a|an)\s+)?(musical|documentary)\s+about\s+(.+)$/i

export function expandQuery(query, config) {
  const normalized = query.toLowerCase()
  const additions = config.expansions
    .filter((rule) => rule.terms?.some((term) => normalized.includes(term)) || (rule.all_terms && rule.all_terms.every((term) => normalized.includes(term))))
    .map((rule) => rule.append)
  return additions.length ? [query, ...additions].join(' ') : query
}

function hasUsableKeywords(movie) {
  return Boolean(movie.has_keywords && Array.isArray(movie.keyword_embedding) && movie.keyword_embedding.some((value) => value !== 0))
}

function movieText(movie) {
  return [movie.title, movie.overview, ...(movie.genres || []), ...(movie.keywords || [])].join(' ').toLowerCase()
}

function shouldShowEmpty(query, topTen, allScores, config) {
  const structured = query.trim().match(STRUCTURED_QUERY)
  if (structured) {
    const [, requestedGenre, subject] = structured
    const genreWords = config.structured_genres[requestedGenre.toLowerCase()] || [requestedGenre.toLowerCase()]
    const subjectWords = (subject.toLowerCase().match(/[a-z]{3,}/g) || []).filter((word) => !STOP_WORDS.has(word))
    const supportsWholeRequest = topTen.some(({ movie }) => {
      const genreSource = (requestedGenre.toLowerCase() === 'documentary' ? movie.genres : [...(movie.genres || []), ...(movie.keywords || [])]).join(' ').toLowerCase()
      const text = movieText(movie)
      return genreWords.some((word) => genreSource.includes(word)) && subjectWords.every((word) => text.includes(word))
    })
    if (!supportsWholeRequest) return true
  }

  const topScore = topTen[0].score
  const averageScore = allScores.reduce((total, score) => total + score, 0) / allScores.length
  return topScore < .14 && topScore - averageScore < .06
}

function confidenceFromRank(score, referenceScores) {
  const highest = referenceScores[0]
  const lowest = referenceScores[referenceScores.length - 1]
  const relative = (score - lowest) / Math.max(highest - lowest, 1e-6)
  const label = relative >= .67 ? 'High confidence' : relative >= .34 ? 'Medium confidence' : 'Low confidence'
  return { label, percentage: Math.round(54 + 42 * Math.max(0, Math.min(1, relative))) }
}

export function rankMovieMatches(query, queryVector, movies, config, limit = 8) {
  const allScored = movies.map((movie) => {
    const contentScore = dotProduct(movie.embedding, queryVector)
    const keywordScore = dotProduct(movie.keyword_embedding, queryVector)
    const score = hasUsableKeywords(movie)
      ? config.content_weight * contentScore + config.keyword_weight * keywordScore
      : contentScore
    return { movie, contentScore, keywordScore, score }
  }).sort((left, right) => right.score - left.score)

  const reference = allScored.slice(0, limit)
  const referenceScores = reference.map((row) => row.score)
  const allScores = allScored.map((row) => row.score)
  const isEmpty = shouldShowEmpty(query, allScored.slice(0, 10), allScores, config)
  return {
    isEmpty,
    matches: reference.map((row) => ({ ...row, confidence: confidenceFromRank(row.score, referenceScores) })),
  }
}

export function dotProduct(left, right) {
  let score = 0
  for (let index = 0; index < left.length; index += 1) score += left[index] * right[index]
  return score
}
