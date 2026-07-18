// Executes the same ranking module that the Vite frontend imports, using fp32 Transformers.js.
import { readFile } from 'node:fs/promises'
import { env, pipeline } from '@xenova/transformers'
import { expandQuery, rankMovieMatches } from '../src/data/searchRanking.js'

const queries = [
  'a slow burn romance where they just talk all night',
  'getting over a breakup but making it cute',
  "falling in love with someone you're not supposed to",
  'a love story that breaks your heart at the end',
  'nothing is what it seems',
  "a twist I didn't see coming",
  'rich people behaving badly',
  'an unreliable narrator',
  'hopeful but kind of sad at the same time',
  'cozy but makes you cry',
  'big scale but still feels personal',
  'a dream within a dream kind of confusion',
  "something to watch when I'm sick and want to feel less alone",
  'a movie that makes prison feel hopeful somehow',
  'long distance relationship but make it space',
  'second chance love story',
  'a musical about time travel',
  'documentary about deep sea creatures',
]

const [data, config] = await Promise.all([
  readFile('public/data/movies_data.json', 'utf8').then(JSON.parse),
  readFile('public/data/search_config.json', 'utf8').then(JSON.parse),
])
env.allowLocalModels = false
env.useBrowserCache = false
const extractor = await pipeline('feature-extraction', 'Xenova/all-MiniLM-L6-v2', { quantized: false })

for (const query of queries) {
  const output = await extractor(expandQuery(query, config), { pooling: 'mean', normalize: true })
  const ranked = rankMovieMatches(query, output.data, data.movies, config, 8)
  console.log(JSON.stringify({
    query,
    show_empty: ranked.isEmpty,
    top_3: ranked.matches.slice(0, 3).map(({ movie, score, confidence }) => ({ title: movie.title, score: Number(score.toFixed(4)), confidence: confidence.label })),
  }))
}
