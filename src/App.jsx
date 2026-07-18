import { useEffect, useLayoutEffect, useRef, useState } from 'react'
import Lenis from 'lenis'
import { gsap } from 'gsap'
import { ScrollTrigger } from 'gsap/ScrollTrigger'
import { ArrowLeft, ArrowRight, ArrowUpRight, BrainCircuit, Check, Clock3, Play, Sparkles } from 'lucide-react'
import { movies } from './data/movies'
import { MoodSearch } from './components/MoodSearch'
import { MiniCurve, TensionCurve } from './components/TensionCurve'

gsap.registerPlugin(ScrollTrigger)

function useReducedMotion() {
  const [reduced, setReduced] = useState(() => window.matchMedia('(prefers-reduced-motion: reduce)').matches)
  useEffect(() => { const media = window.matchMedia('(prefers-reduced-motion: reduce)'); const update = () => setReduced(media.matches); media.addEventListener('change', update); return () => media.removeEventListener('change', update) }, [])
  return reduced
}

function useSmoothScroll(disabled) {
  useEffect(() => { if (disabled) return undefined; const lenis = new Lenis({ lerp: 0.085, smoothWheel: true }); let frame; const raf = (time) => { lenis.raf(time); frame = requestAnimationFrame(raf) }; frame = requestAnimationFrame(raf); return () => { cancelAnimationFrame(frame); lenis.destroy() } }, [disabled])
}

function Header({ view, query, onSearch, onHome, onHowItWorks }) {
  return <header className={`site-header ${view === 'results' ? 'site-header--searching' : ''}`}>
    <button className="wordmark" onClick={onHome} aria-label="CineMood home">cine<span>mood</span></button>
    {view === 'results' && <div className="header-search"><MoodSearch key={query} compact initialValue={query} onSearch={onSearch} label="Search another feeling" /></div>}
    <nav aria-label="Primary navigation">{view !== 'search' && <button className="nav-back" onClick={onHome}><ArrowLeft size={14} /> new search</button>}<button onClick={onHowItWorks}>how it works <ArrowUpRight size={14} /></button></nav>
  </header>
}

function Opening({ onEnter }) {
  const introRef = useRef(null); const reduced = useReducedMotion()
  useLayoutEffect(() => { if (reduced || !introRef.current) return undefined; const context = gsap.context(() => { const timeline = gsap.timeline({ defaults: { ease: 'power3.out' } }); timeline.from('.opening-mark span', { opacity: 0, y: 30, filter: 'blur(10px)', duration: 1.2, stagger: .09 }).from('.opening-tagline, .opening-cta', { opacity: 0, y: 14, duration: .7, stagger: .13 }, '-=.45') }, introRef); return () => context.revert() }, [reduced])
  return <main className="opening" ref={introRef}><div className="opening-light" aria-hidden="true" /><div className="opening-content"><h1 className="opening-mark" aria-label="CineMood"><span>cine</span><span>mood</span></h1><p className="opening-tagline">Discover films by emotion, not by genre.</p><button className="opening-cta" onClick={onEnter}>Enter CineMood <ArrowRight size={17} /></button></div></main>
}

function Intro({ onSearch }) {
  const heroRef = useRef(null); const reduced = useReducedMotion()
  useLayoutEffect(() => { if (reduced || !heroRef.current) return undefined; const context = gsap.context(() => { gsap.from('.hero-copy > *, .hero-search-cluster > *', { y: 22, opacity: 0, duration: .85, stagger: .1, ease: 'power3.out' }) }, heroRef); return () => context.revert() }, [reduced])
  return <>
    <main className="hero" ref={heroRef}>
      <div className="hero-halo" aria-hidden="true" />
      <div className="hero-copy"><p className="eyebrow"><span className="live-dot" /> semantic film discovery</p><h1>Tell us how you<br /><em>want to feel.</em></h1><p className="hero-sub">CineMood understands meaning—not keywords or genres—to find films that move at the same emotional frequency.</p></div>
      <div className="hero-search-cluster"><MoodSearch onSearch={onSearch} /><div className="search-promise"><span><BrainCircuit size={15} /> semantic AI search</span><i /><span>your words stay human</span></div></div>
      <div className="flow-proof" aria-label="How CineMood works"><span>describe a feeling</span><ArrowRight size={15} /><span>AI reads the meaning</span><ArrowRight size={15} /><span>find your film</span></div>
    </main>
    <HowItWorks />
  </>
}

function AnalysisScreen({ step, query }) {
  const steps = ['Understanding your mood…', 'Generating semantic embedding…', 'Comparing against movie embeddings…', 'Ranking emotional similarity…']
  return <main className="analysis-screen" aria-live="polite"><div className="analysis-orbit" aria-hidden="true"><i /><i /><i /></div><div className="analysis-copy"><p className="eyebrow"><Sparkles size={13} /> CineMood AI</p><h1>{steps[step]}</h1><p>Looking beyond “{query}” to its emotional shape, pace, and subtext.</p></div><div className="analysis-steps">{steps.map((item, index) => <div className={index < step ? 'is-done' : index === step ? 'is-current' : ''} key={item}><span>{index < step ? <Check size={12} /> : String(index + 1).padStart(2, '0')}</span>{item}</div>)}</div></main>
}

function ScoreRing({ score }) {
  return <div className="best-score" aria-label={`${score} percent semantic match`}><svg viewBox="0 0 42 42" aria-hidden="true"><circle className="score-track" cx="21" cy="21" r="18" pathLength="100" /><circle className="score-progress" cx="21" cy="21" r="18" pathLength="100" strokeDasharray="100" strokeDashoffset={100 - score} /></svg><div><strong>{score}<small>%</small></strong><span>semantic<br />match</span></div></div>
}

function BestMatch({ movie, onOpen }) {
  return <article className="best-match"><div className="best-poster"><img src={movie.poster} alt={`Poster-style still for ${movie.title}`} /><span className="best-label"><Sparkles size={13} /> Best match</span><ScoreRing score={movie.match} /></div><div className="best-copy"><p className="eyebrow">CineMood’s first choice</p><h2>{movie.title} <span>({movie.year})</span></h2><div className="metadata"><span><Clock3 size={14} /> {movie.duration}</span><span>{movie.mood}</span></div><p className="best-summary">{movie.summary}</p><div className="match-reasons"><span>Similar emotional pacing</span><span>Quiet emotional ending</span><span>Themes of grief &amp; hope</span></div><button className="timeline-cta" onClick={() => onOpen(movie)}>Explore emotional timeline <ArrowRight size={17} /></button></div></article>
}

function MovieCard({ movie, index, onOpen }) {
  const level = movie.match >= 90 ? 'exceptional' : movie.match >= 80 ? 'strong' : 'possible'
  return <button className="movie-card" onClick={() => onOpen(movie)} aria-label={`Explore ${movie.title}`}><div className="poster-frame"><img src={movie.poster} alt={`Poster-style still for ${movie.title}`} /><span className="card-index">0{index + 2}</span><span className={`confidence confidence--${level}`}>{movie.match}%<small> match</small></span></div><div className="card-copy"><div><h2>{movie.title}</h2><p>{movie.year} <span>—</span> {movie.duration}</p></div><span className="open-icon"><ArrowUpRight size={18} /></span></div><div className="mini-arc-row"><MiniCurve movie={movie} /><span>{movie.mood}</span></div><p className="card-reason">{movie.reason}</p></button>
}

function Results({ query, onMovie, onSearch }) {
  const resultsRef = useRef(null); const reduced = useReducedMotion()
  useLayoutEffect(() => { if (reduced || !resultsRef.current) return undefined; const context = gsap.context(() => { gsap.from('.best-match', { opacity: 0, y: 30, duration: .85, ease: 'power3.out' }); gsap.from('.score-progress', { strokeDashoffset: 100, duration: 1.35, delay: .35, ease: 'power3.out' }); gsap.from('.movie-card', { opacity: 0, y: 28, stagger: .11, duration: .7, ease: 'power3.out', scrollTrigger: { trigger: '.more-matches', start: 'top 83%', once: true } }) }, resultsRef); return () => context.revert() }, [reduced, query])
  return <main className="results-page" ref={resultsRef}><section className="results-intro"><p className="eyebrow"><Sparkles size={13} /> Semantic match complete</p><h1>We found the feeling<br />inside <em>“{query}”</em></h1><p>Ranked by emotional resemblance, not genre labels.</p></section><BestMatch movie={movies[0]} onOpen={onMovie} /><section className="more-matches"><div className="section-heading"><div><p className="eyebrow">Continue the reel</p><h2>More ways into the mood.</h2></div><span>03 recommendations</span></div><div className="movie-grid">{movies.slice(1).map((movie, index) => <MovieCard key={movie.id} movie={movie} index={index} onOpen={onMovie} />)}</div></section><HowItWorks /></main>
}

function Detail({ movie, onBack }) {
  const detailRef = useRef(null); const reduced = useReducedMotion()
  useLayoutEffect(() => { if (reduced || !detailRef.current) return undefined; const context = gsap.context(() => { gsap.from('.detail-head > *, .curve-wrap, .detail-context > *', { opacity: 0, y: 22, duration: .8, stagger: .09, ease: 'power3.out' }); gsap.from('.curve-line', { strokeDasharray: 150, strokeDashoffset: 150, duration: 1.6, delay: .35, ease: 'power2.out' }) }, detailRef); return () => context.revert() }, [movie, reduced])
  return <main className="detail-page" ref={detailRef}><button className="detail-back" onClick={onBack}><ArrowLeft size={17} /> all matches</button><section className="detail-head"><div><p className="eyebrow">Emotional evidence / {movie.match}% semantic match</p><h1>{movie.title} <span>({movie.year})</span></h1></div><div className="metadata"><span><Clock3 size={14} /> {movie.duration}</span><span>{movie.mood}</span></div></section><TensionCurve movie={movie} /><section className="detail-context"><div className="detail-poster"><img src={movie.poster} alt={`Poster-style still for ${movie.title}`} /><span className="poster-play"><Play size={17} fill="currentColor" /></span></div><div className="detail-copy"><p>{movie.summary}</p><div className="detail-reason"><span>why it matched</span>{movie.reason}</div><p className="model-note">CineMood maps the feeling of a story over time. It’s an invitation to explore, not a verdict on the film.</p></div></section></main>
}

function HowItWorks() {
  const sectionRef = useRef(null); const reduced = useReducedMotion()
  useLayoutEffect(() => { if (reduced || !sectionRef.current) return undefined; const context = gsap.context(() => { gsap.from('.step', { opacity: 0, y: 24, stagger: .1, duration: .65, ease: 'power2.out', scrollTrigger: { trigger: sectionRef.current, start: 'top 82%', once: true } }) }, sectionRef); return () => context.revert() }, [reduced])
  return <section className="how-it-works" ref={sectionRef} id="how-it-works"><div className="how-title"><p className="eyebrow">The quiet machinery</p><h2>Film discovery with<br />a little more feeling.</h2><p>CineMood turns natural language into emotional similarity—so “what should I watch?” can start with something honest.</p></div><div className="steps"><article className="step"><span>01</span><h3>Say it naturally</h3><p>A mood, a scene, an aftertaste. There is no right query.</p></article><article className="step"><span>02</span><h3>Meaning takes shape</h3><p>Embeddings translate the feeling behind your words—not just their keywords.</p></article><article className="step"><span>03</span><h3>Stories are compared</h3><p>We search for films with an emotionally similar narrative signature.</p></article><article className="step"><span>04</span><h3>See the whole ride</h3><p>A sentiment model makes the tension and release legible before you press play.</p></article></div></section>
}

export default function App() {
  const [view, setView] = useState('intro'); const [query, setQuery] = useState('a quiet devastating ending'); const [selected, setSelected] = useState(movies[0]); const [analysisStep, setAnalysisStep] = useState(0); const reduced = useReducedMotion(); useSmoothScroll(reduced)
  useEffect(() => { if (view !== 'analysis') return undefined; const duration = reduced ? 120 : 720; if (analysisStep >= 3) { const done = window.setTimeout(() => { setView('results'); window.scrollTo(0, 0) }, duration); return () => window.clearTimeout(done) } const next = window.setTimeout(() => setAnalysisStep((current) => current + 1), duration); return () => window.clearTimeout(next) }, [view, analysisStep, reduced])
  function beginSearch(nextQuery) { setQuery(nextQuery); setAnalysisStep(0); setView('analysis'); window.scrollTo(0, 0) }
  function showDetail(movie) { setSelected(movie); setView('detail'); window.scrollTo({ top: 0, behavior: reduced ? 'auto' : 'smooth' }) }
  function goHome() { setView('search'); window.scrollTo({ top: 0, behavior: reduced ? 'auto' : 'smooth' }) }
  function showHow() { const target = document.querySelector('#how-it-works'); if (target) { target.scrollIntoView({ behavior: reduced ? 'auto' : 'smooth' }); return } setView('search'); window.setTimeout(() => document.querySelector('#how-it-works')?.scrollIntoView({ behavior: reduced ? 'auto' : 'smooth' }), 0) }
  function followCursor(event) { if (reduced) return; event.currentTarget.style.setProperty('--cursor-x', `${event.clientX}px`); event.currentTarget.style.setProperty('--cursor-y', `${event.clientY}px`) }
  return <div className={`app-shell app-shell--${view}`} onPointerMove={followCursor}>{view !== 'intro' && <><div className="ambient-cursor" aria-hidden="true" /><div className="film-grain" aria-hidden="true" /><Header view={view} query={query} onSearch={beginSearch} onHome={goHome} onHowItWorks={showHow} /></>}{view === 'intro' && <Opening onEnter={() => { setView('search'); window.scrollTo(0, 0) }} />}{view === 'search' && <Intro onSearch={beginSearch} />}{view === 'analysis' && <AnalysisScreen step={analysisStep} query={query} />}{view === 'results' && <Results query={query} onMovie={showDetail} onSearch={beginSearch} />}{view === 'detail' && <Detail movie={selected} onBack={() => setView('results')} />}{view !== 'intro' && <footer><span>CINEMOOD / 2026</span><span>MADE FOR AFTER HOURS</span></footer>}</div>
}
