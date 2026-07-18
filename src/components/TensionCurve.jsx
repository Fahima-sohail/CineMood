import { Info } from 'lucide-react'
import { useId, useState } from 'react'

function getPoint(index, value, count) {
  return [5 + (index / (count - 1)) * 90, 88 - value * 0.72]
}

export function MiniCurve({ movie }) {
  const gradientId = useId().replace(/:/g, '')
  const points = movie.curve.map((value, index) => getPoint(index, value, movie.curve.length))
  const path = points.map(([x, y], index) => `${index === 0 ? 'M' : 'L'} ${x} ${y}`).join(' ')
  return <svg className="mini-curve" viewBox="0 0 100 100" preserveAspectRatio="none" aria-label="Emotional arc preview"><defs><linearGradient id={gradientId} x1="0%" x2="100%"><stop stopColor="#4FA8A0" /><stop offset="100%" stopColor="#D4A054" /></linearGradient></defs><path d={path} fill="none" stroke={`url(#${gradientId})`} /></svg>
}

export function TensionCurve({ movie }) {
  const gradientId = useId().replace(/:/g, '')
  const [active, setActive] = useState(2)
  const points = movie.curve.map((value, index) => getPoint(index, value, movie.curve.length))
  const path = points.map(([x, y], index) => `${index === 0 ? 'M' : 'L'} ${x} ${y}`).join(' ')
  const area = `${path} L 95 95 L 5 95 Z`
  const milestones = [
    { point: 0, title: 'Beginning', detail: 'The film opens with room to settle into its world.', tone: 'teal' },
    { point: 5, title: 'Turning point', detail: 'Questions begin to gather and the pace tightens.', tone: 'amber' },
    { point: 12, title: 'Emotional peak', detail: 'Its central feeling reaches its most intense point.', tone: 'amber' },
    { point: 14, title: 'Resolution', detail: 'The emotional weight begins to release.', tone: 'teal' },
    { point: 15, title: 'Ending', detail: 'The story lands on a reflective final note.', tone: 'teal' },
  ]

  return (
    <section className="curve-wrap" aria-labelledby="curve-title">
      <div className="curve-heading">
        <div><p className="eyebrow">Emotional evidence</p><h2 id="curve-title">A journey you can feel at a glance.</h2></div>
        <div className="curve-legend" aria-label="Emotional timeline color legend"><span className="legend-calm" /> calm <span className="legend-tense" /> heightened</div>
      </div>
      <div className="milestone-list" aria-label="Emotional timeline milestones">
        {milestones.map((milestone, index) => <button key={milestone.title} className={`milestone milestone--${milestone.tone} ${active === index ? 'is-active' : ''}`} onClick={() => setActive(index)} onMouseEnter={() => setActive(index)} aria-pressed={active === index}><span>{String(index + 1).padStart(2, '0')}</span>{milestone.title}</button>)}
      </div>
      <div className="chart" role="group" aria-label={`Interactive emotional timeline for ${movie.title}`}>
        <div className="chart-label chart-label--high">heightened</div><div className="chart-label chart-label--low">stillness</div>
        <svg viewBox="0 0 100 100" preserveAspectRatio="none" aria-hidden="true">
          <defs><linearGradient id={gradientId} x1="0%" y1="0%" x2="100%" y2="0%"><stop offset="0%" stopColor="#4FA8A0" /><stop offset="54%" stopColor="#7e9f86" /><stop offset="100%" stopColor="#D4A054" /></linearGradient></defs>
          {[20, 45, 70, 95].map((y) => <line key={y} x1="5" x2="95" y1={y} y2={y} className="gridline" />)}
          <path d={area} fill={`url(#${gradientId})`} className="curve-area" /><path d={path} fill="none" stroke={`url(#${gradientId})`} className="curve-line" />
          {milestones.map(({ point, tone }, index) => { const [x, y] = points[point]; return <circle key={point} cx={x} cy={y} r={active === index ? '2.1' : '1.3'} className={`curve-dot curve-dot--${tone} ${active === index ? 'is-active' : ''}`} /> })}
        </svg>
        {milestones.map(({ point, title, detail, tone }, index) => { const [x, y] = points[point]; return <button className={`curve-note curve-note--${tone} ${active === index ? 'is-active' : ''}`} style={{ left: `${x}%`, top: `${Math.max(y - 17, 3)}%` }} key={title} onClick={() => setActive(index)} onMouseEnter={() => setActive(index)} aria-label={`${title}: ${detail}`}><span>{title}</span>{active === index && <small>{detail}</small>}</button> })}
      </div>
      <div className="timeline"><span>00:00</span><span>middle</span><span>{movie.duration}</span></div>
      <p className="timeline-help"><Info size={13} /> Select any milestone to understand what changes in the film’s emotional pace.</p>
    </section>
  )
}
