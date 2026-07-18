import { useEffect, useLayoutEffect, useRef, useState } from 'react'
import Lenis from 'lenis'
import { gsap } from 'gsap'
import { ScrollTrigger } from 'gsap/ScrollTrigger'
import { ArrowLeft, ArrowRight, ArrowUpRight, BrainCircuit, Check, Clock3, Play, Sparkles, Star } from 'lucide-react'
import { searchMovies } from './data/semanticSearch'
import { MoodSearch } from './components/MoodSearch'
import { MiniCurve, TensionCurve } from './components/TensionCurve'

gsap.registerPlugin(ScrollTrigger)

function useReducedMotion() {
  const [reduced, setReduced] = useState(() => window.matchMedia('(prefers-reduced-motion: reduce)').matches)
  useEffect(() => {
    const media = window.matchMedia('(prefers-reduced-motion: reduce)')
    const update = () => setReduced(media.matches)
    media.addEventListener('change', update)
    return () => media.removeEventListener('change', update)
  }, [])
  return reduced
}

function useSmoothScroll(disabled) {
  useEffect(() => {
    if (disabled) return undefined
    const lenis = new Lenis({ lerp: .085, smoothWheel: true })
    let frame
    const raf = (time) => { lenis.raf(time); frame = requestAnimationFrame(raf) }
    frame = requestAnimationFrame(raf)
    return () => { cancelAnimationFrame(frame); lenis.destroy() }
  }, [disabled])
}

function Header({ view, query, onSearch, onHome, onHowItWorks }) {
  return <header className={`site-header ${view === 'results' ? 'site-header--searching' : ''}`}>
    <button className="wordmark" onClick={onHome} aria-label="CineMood home">cine<span>mood</span></button>
    {view === 'results' && <div className="header-search"><MoodSearch key={query} compact initialValue={query} onSearch={onSearch} label="Search another feeling" /></div>}
    <nav aria-label="Primary navigation">
      {view !== 'search' && <button className="nav-back" onClick={onHome}><ArrowLeft size={14} /> new search</button>}
      <button onClick={onHowItWorks}>how it works <ArrowUpRight size={14} /></button>
    </nav>
  </header>
}

function Opening({ onEnter }) {
  const introRef = useRef(null)
  const reduced = useReducedMotion()
  useLayoutEffect(() => {
    if (reduced || !introRef.current) return undefined
    const context = gsap.context(() => {
      gsap.timeline({ defaults: { ease: 'power3.out' } })
        .from('.opening-mark span', { opacity: 0, y: 30, filter: 'blur(10px)', duration: 1.2, stagger: .09 })
        .from('.opening-tagline, .opening-cta', { opacity: 0, y: 14, duration: .7, stagger: .13 }, '-=.45')
    }, introRef)
    return () => context.revert()
  }, [reduced])
  return <main className="opening" ref={introRef}><div className="opening-light" aria-hidden="true" /><div className="opening-content"><h1 className="opening-mark" aria-label="CineMood"><span>cine</span><span>mood</span></h1><p className="opening-tagline">Discover films by emotion, not by genre.</p><button className="opening-cta" onClick={onEnter}>Enter CineMood <ArrowRight size={17} /></button></div></main>
}

function SearchLanding({ onSearch }) {
  const heroRef = useRef(null)
  const reduced = useReducedMotion()
  useLayoutEffect(() => {
    if (reduced || !heroRef.current) return undefined
    const context = gsap.context(() => gsap.from('.hero-copy > *, .hero-search-cluster > *', { y: 22, opacity: 0, duration: .85, stagger: .1, ease: 'power3.out' }), heroRef)
    return () => context.revert()
  }, [reduced])
  return <>
    <main className="hero" ref={heroRef}>
      <div className="hero-halo" aria-hidden="true" />
      <div className="hero-copy"><p className="eyebrow"><span className="live-dot" /> semantic film discovery</p><h1>Tell us how you<br /><em>want to feel.</em></h1><p className="hero-sub">CineMood understands meaning—not keywords or genres—to find films that move at the same emotional frequency.</p></div>
      <div className="hero-search-cluster"><MoodSearch onSearch={onSearch} /><div className="search-promise"><span><BrainCircuit size={15} /> MiniLM runs on this device</span><i /><span>no live movie API</span></div></div>
      <div className="flow-proof" aria-label="How CineMood works"><span>describe a feeling</span><ArrowRight size={15} /><span>AI embeds the meaning</span><ArrowRight size={15} /><span>find your film</span></div>
    </main>
    <HowItWorks />
  </>
}

function AnalysisScreen({ phase, progress, query, error }) {
  const steps = ['Warming the local AI model…', 'Embedding your feeling…', 'Comparing 310 film vectors…', 'Ranking semantic similarity…']
  const phaseIndex = { model: 0, data: 0, embedding: 1, comparing: 2, ranking: 3, complete: 3, error: 0 }
  const activeStep = phaseIndex[phase] ?? 0
  const downloadPercent = phase === 'model' && progress?.progress ? ` ${Math.round(progress.progress)}%` : ''
  return <main className="analysis-screen" aria-live="polite"><div className="analysis-orbit" aria-hidden="true"><i /><i /><i /></div><div className="analysis-copy"><p className="eyebrow"><Sparkles size={13} /> CineMood AI / on this device</p><h1>{error ? 'The local model could not start.' : `${steps[activeStep]}${downloadPercent}`}</h1><p>{error || `Turning “${query}” into a MiniLM vector, then comparing it with the offline CineMood collection.`}</p></div><div className="analysis-steps">{steps.map((item, index) => <div className={index < activeStep ? 'is-done' : index === activeStep ? 'is-current' : ''} key={item}><span>{index < activeStep ? <Check size={12} /> : String(index + 1).padStart(2, '0')}</span>{item}</div>)}</div></main>
}

function ScoreRing({ score, label }) {
  return <div className="best-score" aria-label={`${score} percent ${label}`}><svg viewBox="0 0 42 42" aria-hidden="true"><circle className="score-track" cx="21" cy="21" r="18" pathLength="100" /><circle className="score-progress" cx="21" cy="21" r="18" pathLength="100" strokeDasharray="100" strokeDashoffset={100 - score} /></svg><div><strong>{score}<small>%</small></strong><span>semantic<br />match</span></div></div>
}

function BestMatch({ movie, onOpen }) {
  return <article className="best-match"><div className="best-poster"><img src={movie.poster} alt={`Poster for ${movie.title}`} /><span className="best-label"><Sparkles size={13} /> {movie.confidenceLabel}</span><ScoreRing score={movie.match} label={movie.confidenceLabel} /></div><div className="best-copy"><p className="eyebrow">CineMood’s first choice</p><h2>{movie.title} <span>({movie.year})</span></h2><div className="metadata"><span><Clock3 size={14} /> {movie.duration}</span><span><Star size={14} /> {movie.voteAverage?.toFixed?.(1) ?? movie.voteAverage} TMDb</span><span>{movie.mood}</span></div><p className="best-summary">{movie.summary}</p><div className="match-reasons">{movie.matchReasons.map((reason) => <span key={reason}>{reason}</span>)}</div><button className="timeline-cta" onClick={() => onOpen(movie)}>Explore emotional timeline <ArrowRight size={17} /></button></div></article>
}

function MovieCard({ movie, index, onOpen }) {
  const level = movie.match >= 85 ? 'exceptional' : movie.match >= 70 ? 'strong' : 'possible'
  return <button className="movie-card" onClick={() => onOpen(movie)} aria-label={`Explore ${movie.title}`}><div className="poster-frame"><img src={movie.poster} alt={`Poster for ${movie.title}`} /><span className="card-index">0{index + 2}</span><span className={`confidence confidence--${level}`}>{movie.match}%<small>{movie.confidenceLabel}</small></span></div><div className="card-copy"><div><h2>{movie.title}</h2><p>{movie.year} <span>—</span> {movie.duration}</p></div><span className="open-icon"><ArrowUpRight size={18} /></span></div><div className="mini-arc-row"><MiniCurve movie={movie} /><span>{movie.mood} · {movie.voteAverage?.toFixed?.(1) ?? movie.voteAverage} TMDb</span></div><p className="card-reason">{movie.reason}</p></button>
}

function Results({ query, matches, onMovie }) {
  const resultsRef = useRef(null)
  const reduced = useReducedMotion()
  useLayoutEffect(() => {
    if (reduced || !resultsRef.current) return undefined
    const context = gsap.context(() => { gsap.from('.best-match', { opacity: 0, y: 30, duration: .85, ease: 'power3.out' }); gsap.from('.score-progress', { strokeDashoffset: 100, duration: 1.35, delay: .35, ease: 'power3.out' }); gsap.from('.movie-card', { opacity: 0, y: 28, stagger: .11, duration: .7, ease: 'power3.out', scrollTrigger: { trigger: '.more-matches', start: 'top 83%', once: true } }) }, resultsRef)
    return () => context.revert()
  }, [reduced, query])
  return <main className="results-page" ref={resultsRef}><section className="results-intro"><p className="eyebrow"><Sparkles size={13} /> Local semantic search complete</p><h1>We found the feeling<br />inside <em>“{query}”</em></h1><p>310 curated TMDb films ranked by MiniLM cosine similarity—entirely in your browser.</p></section><BestMatch movie={matches[0]} onOpen={onMovie} /><section className="more-matches"><div className="section-heading"><div><p className="eyebrow">Continue the reel</p><h2>More ways into the mood.</h2></div><span>{String(matches.length - 1).padStart(2, '0')} recommendations</span></div><div className="movie-grid">{matches.slice(1).map((movie, index) => <MovieCard key={movie.id} movie={movie} index={index} onOpen={onMovie} />)}</div></section><HowItWorks /></main>
}

function Detail({ movie, onBack }) {
  const detailRef = useRef(null)
  const reduced = useReducedMotion()
  useLayoutEffect(() => {
    if (reduced || !detailRef.current) return undefined
    const context = gsap.context(() => { gsap.from('.detail-head > *, .curve-wrap, .detail-context > *', { opacity: 0, y: 22, duration: .8, stagger: .09, ease: 'power3.out' }); gsap.from('.curve-line', { strokeDasharray: 150, strokeDashoffset: 150, duration: 1.6, delay: .35, ease: 'power2.out' }) }, detailRef)
    return () => context.revert()
  }, [movie, reduced])
  return <main className="detail-page" ref={detailRef}><button className="detail-back" onClick={onBack}><ArrowLeft size={17} /> all matches</button><section className="detail-head"><div><p className="eyebrow">Emotional evidence / {movie.match}% {movie.confidenceLabel.toLowerCase()}</p><h1>{movie.title} <span>({movie.year})</span></h1></div><div className="metadata"><span><Clock3 size={14} /> {movie.duration}</span><span><Star size={14} /> {movie.voteAverage?.toFixed?.(1) ?? movie.voteAverage} TMDb</span><span>{movie.mood}</span></div></section><TensionCurve movie={movie} /><section className="detail-context"><div className="detail-poster"><img src={movie.poster} alt={`Poster for ${movie.title}`} /><span className="poster-play"><Play size={17} fill="currentColor" /></span></div><div className="detail-copy"><p>{movie.summary}</p><div className="detail-reason"><span>why it matched</span>{movie.reason}</div><p className="model-note">Placeholder emotional curve: the sentiment-classifier stage will replace this visual prototype with a real movie timeline.</p></div></section></main>
}

function HowItWorks() {
  const sectionRef = useRef(null)
  const reduced = useReducedMotion()
  useLayoutEffect(() => {
    if (reduced || !sectionRef.current) return undefined
    const context = gsap.context(() => gsap.from('.step', { opacity: 0, y: 24, stagger: .1, duration: .65, ease: 'power2.out', scrollTrigger: { trigger: sectionRef.current, start: 'top 82%', once: true } }), sectionRef)
    return () => context.revert()
  }, [reduced])
  return <section className="how-it-works" ref={sectionRef} id="how-it-works"><div className="how-title"><p className="eyebrow">The quiet machinery</p><h2>Film discovery with<br />a little more feeling.</h2><p>CineMood turns natural language into emotional similarity—so “what should I watch?” can start with something honest.</p></div><div className="steps"><article className="step"><span>01</span><h3>Say it naturally</h3><p>A mood, a scene, an aftertaste. There is no right query.</p></article><article className="step"><span>02</span><h3>Meaning takes shape</h3><p>MiniLM embeds the feeling behind your words—not just their keywords.</p></article><article className="step"><span>03</span><h3>Films are compared</h3><p>Cosine similarity ranks the 310 local movie vectors.</p></article><article className="step"><span>04</span><h3>See the whole ride</h3><p>A sentiment model will add real tension curves in the next pipeline step.</p></article></div></section>
}

export default function App() {
  const [view, setView] = useState('intro')
  const [query, setQuery] = useState('a quiet devastating ending')
  const [matches, setMatches] = useState([])
  const [selected, setSelected] = useState(null)
  const [searchState, setSearchState] = useState({ phase: 'model', progress: null, error: null })
  const reduced = useReducedMotion()
  useSmoothScroll(reduced)

  async function beginSearch(nextQuery) {
    setQuery(nextQuery)
    setSearchState({ phase: 'model', progress: null, error: null })
    setView('analysis')
    window.scrollTo(0, 0)
    try {
      const nextMatches = await searchMovies(nextQuery, { onProgress: ({ phase, event }) => setSearchState({ phase, progress: event, error: null }) })
      setMatches(nextMatches)
      setSelected(nextMatches[0])
      setSearchState({ phase: 'complete', progress: null, error: null })
      window.setTimeout(() => { setView('results'); window.scrollTo(0, 0) }, reduced ? 0 : 360)
    } catch (error) {
      console.error(error)
      setSearchState({ phase: 'error', progress: null, error: 'Check your connection once so the browser can cache the MiniLM model, then try the search again.' })
    }
  }

  function showDetail(movie) { setSelected(movie); setView('detail'); window.scrollTo({ top: 0, behavior: reduced ? 'auto' : 'smooth' }) }
  function goHome() { setView('search'); window.scrollTo({ top: 0, behavior: reduced ? 'auto' : 'smooth' }) }
  function showHow() { const target = document.querySelector('#how-it-works'); if (target) { target.scrollIntoView({ behavior: reduced ? 'auto' : 'smooth' }); return } setView('search'); window.setTimeout(() => document.querySelector('#how-it-works')?.scrollIntoView({ behavior: reduced ? 'auto' : 'smooth' }), 0) }
  function followCursor(event) { if (reduced) return; event.currentTarget.style.setProperty('--cursor-x', `${event.clientX}px`); event.currentTarget.style.setProperty('--cursor-y', `${event.clientY}px`) }

  return <div className={`app-shell app-shell--${view}`} onPointerMove={followCursor}>{view !== 'intro' && <><div className="ambient-cursor" aria-hidden="true" /><div className="film-grain" aria-hidden="true" /><Header view={view} query={query} onSearch={beginSearch} onHome={goHome} onHowItWorks={showHow} /></>}{view === 'intro' && <Opening onEnter={() => { setView('search'); window.scrollTo(0, 0) }} />}{view === 'search' && <SearchLanding onSearch={beginSearch} />}{view === 'analysis' && <AnalysisScreen {...searchState} query={query} />}{view === 'results' && matches.length > 0 && <Results query={query} matches={matches} onMovie={showDetail} />}{view === 'detail' && selected && <Detail movie={selected} onBack={() => setView('results')} />}{view !== 'intro' && <footer><span>CINEMOOD / 2026</span><span>MADE FOR AFTER HOURS</span></footer>}</div>
}
