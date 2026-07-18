import { ArrowUpRight, Sparkles } from 'lucide-react'
import { useEffect, useState } from 'react'

const examples = ['hope after loss', 'chaotic fun with friends', 'slow psychological dread', 'a quiet devastating ending']

export function MoodSearch({ onSearch, compact = false, initialValue = '', label = 'Describe a mood or moment' }) {
  const [value, setValue] = useState(initialValue)
  const [active, setActive] = useState(false)
  const [exampleIndex, setExampleIndex] = useState(0)
  const bars = Array.from({ length: compact ? 38 : 58 })

  useEffect(() => {
    if (active || value) return undefined
    const interval = window.setInterval(() => setExampleIndex((index) => (index + 1) % examples.length), 2700)
    return () => window.clearInterval(interval)
  }, [active, value])

  function submit(event) {
    event.preventDefault()
    onSearch(value.trim() || 'a quiet devastating ending')
  }

  return (
    <form className={`mood-search ${compact ? 'mood-search--compact' : ''} ${active ? 'is-active' : ''}`} onSubmit={submit}>
      <div className="waveform" aria-hidden="true">
        {bars.map((_, index) => <i key={index} style={{ '--i': index, '--h': `${18 + ((index * 17) % 50)}%` }} />)}
      </div>
      <Sparkles className="search-sparkle" size={compact ? 16 : 18} strokeWidth={1.5} aria-hidden="true" />
      <label className="sr-only" htmlFor={compact ? 'mood-search-small' : 'mood-search'}>{label}</label>
      <input
        id={compact ? 'mood-search-small' : 'mood-search'}
        value={value}
        onChange={(event) => setValue(event.target.value)}
        onFocus={() => setActive(true)}
        onBlur={() => setActive(false)}
        placeholder={active ? 'Describe a feeling, scene, or energy…' : examples[exampleIndex]}
        autoComplete="off"
      />
      <button type="submit" aria-label="Find matching films"><ArrowUpRight size={compact ? 19 : 23} strokeWidth={1.5} /></button>
    </form>
  )
}
