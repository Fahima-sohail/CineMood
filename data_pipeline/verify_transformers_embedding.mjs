// Node verification of the exact Transformers.js embedding call used by the browser.
import { env, pipeline } from '@xenova/transformers'
import { readFile } from 'node:fs/promises'

const sample = 'a slow burn romance where they just talk all night'
env.allowLocalModels = false
env.useBrowserCache = false

const extractor = await pipeline('feature-extraction', 'Xenova/all-MiniLM-L6-v2', { quantized: false })
const output = await extractor(sample, { pooling: 'mean', normalize: true })
const vector = Array.from(output.data)
const magnitude = Math.hypot(...vector)
const pythonProbe = JSON.parse(await readFile('data_pipeline/.cache/python_embedding_probe.json', 'utf8'))
const cosine = vector.reduce((total, value, index) => total + value * pythonProbe.vector[index], 0)
const maxAbsoluteDifference = Math.max(...vector.map((value, index) => Math.abs(value - pythonProbe.vector[index])))
console.log(JSON.stringify({ sample, magnitude, first_8: vector.slice(0, 8), dimensions: vector.length, python_magnitude: Math.hypot(...pythonProbe.vector), cosine_to_python: cosine, max_absolute_difference: maxAbsoluteDifference }))
