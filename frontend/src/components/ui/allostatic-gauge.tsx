'use client'

// SVG arc gauge for Allostatic Score (0-100)
// Zones: 0-40 green, 41-60 yellow, 61-80 red, 81-100 critical

interface AllostaticGaugeProps {
  score: number
  size?: number
}

function scoreColor(score: number): string {
  if (score <= 40) return '#10b981'
  if (score <= 60) return '#f59e0b'
  if (score <= 80) return '#ef4444'
  return '#dc2626'
}

function scoreLabel(score: number): string {
  if (score <= 40) return 'Légère'
  if (score <= 60) return 'Modérée'
  if (score <= 80) return 'Élevée'
  return 'Critique'
}

export function AllostaticGauge({ score, size = 180 }: AllostaticGaugeProps) {
  const cx = size / 2
  const cy = size / 2
  const r = (size * 0.38)
  const strokeW = size * 0.075

  // Arc from 210° to 330° (240° sweep — standard gauge shape)
  const startAngle = 210
  const endAngle = 330 // = 210 + 300 – but we use 210→330 going clockwise = 240° total
  const totalSweep = 300  // degrees

  const toRad = (deg: number) => (deg * Math.PI) / 180

  // Background arc path
  const arcPath = (from: number, to: number) => {
    const s = toRad(from)
    const e = toRad(to)
    const x1 = cx + r * Math.cos(s)
    const y1 = cy + r * Math.sin(s)
    const x2 = cx + r * Math.cos(e)
    const y2 = cy + r * Math.sin(e)
    const large = to - from > 180 ? 1 : 0
    return `M ${x1} ${y1} A ${r} ${r} 0 ${large} 1 ${x2} ${y2}`
  }

  // Score position (0-100 → 210°→510° clockwise, but wrapped)
  const scoreDeg = startAngle + (score / 100) * totalSweep
  const needleAngle = scoreDeg > 360 ? scoreDeg - 360 : scoreDeg

  // Zone arcs: start 210, sweep 300 total
  const zones = [
    { from: 210, to: 210 + 300 * 0.40, color: '#10b98133' },  // 0-40: green bg
    { from: 210 + 300 * 0.40, to: 210 + 300 * 0.60, color: '#f59e0b33' },  // 40-60: yellow bg
    { from: 210 + 300 * 0.60, to: 210 + 300 * 0.80, color: '#ef444433' },  // 60-80: red bg
    { from: 210 + 300 * 0.80, to: 210 + 300, color: '#dc262633' },          // 80-100: critical
  ]

  // Normalize angles >360
  const normTo360 = (deg: number) => ((deg - 1) % 360) + 1

  const color = scoreColor(score)
  const label = scoreLabel(score)

  // Needle tip position
  const needleLength = r * 0.75
  const needleRad = toRad(needleAngle)
  const nx = cx + needleLength * Math.cos(needleRad)
  const ny = cy + needleLength * Math.sin(needleRad)

  // Score arc (filled portion from start to score)
  const scoreArcEnd = scoreDeg > 360 ? scoreDeg - 360 : scoreDeg
  const scoreEndRad = toRad(scoreArcEnd)
  const sax = cx + r * Math.cos(toRad(startAngle))
  const say = cy + r * Math.sin(toRad(startAngle))
  const sex_ = cx + r * Math.cos(scoreEndRad)
  const sey = cy + r * Math.sin(scoreEndRad)
  const scoreSweep = (score / 100) * totalSweep
  const scoreLargeArc = scoreSweep > 180 ? 1 : 0

  return (
    <div className="flex flex-col items-center gap-1">
      <svg width={size} height={size * 0.65} viewBox={`0 0 ${size} ${size}`} style={{ overflow: 'visible' }}>
        {/* Zone background arcs */}
        {zones.map((z, i) => {
          const fs = z.from > 360 ? z.from - 360 : z.from
          const ts = z.to > 360 ? z.to - 360 : z.to
          return (
            <path
              key={i}
              d={arcPath(fs, ts)}
              fill="none"
              stroke={z.color}
              strokeWidth={strokeW}
              strokeLinecap="butt"
            />
          )
        })}

        {/* Score fill arc */}
        {score > 0 && (
          <path
            d={`M ${sax} ${say} A ${r} ${r} 0 ${scoreLargeArc} 1 ${sex_} ${sey}`}
            fill="none"
            stroke={color}
            strokeWidth={strokeW * 0.5}
            strokeLinecap="round"
          />
        )}

        {/* Zone tick marks */}
        {[40, 60, 80].map(pct => {
          const tickAngle = toRad(210 + (pct / 100) * totalSweep)
          const inner = r - strokeW * 0.6
          const outer = r + strokeW * 0.1
          return (
            <line
              key={pct}
              x1={cx + inner * Math.cos(tickAngle)}
              y1={cy + inner * Math.sin(tickAngle)}
              x2={cx + outer * Math.cos(tickAngle)}
              y2={cy + outer * Math.sin(tickAngle)}
              stroke="#22223a"
              strokeWidth={2}
            />
          )
        })}

        {/* Needle */}
        <line
          x1={cx}
          y1={cy}
          x2={nx}
          y2={ny}
          stroke={color}
          strokeWidth={2.5}
          strokeLinecap="round"
        />
        <circle cx={cx} cy={cy} r={size * 0.035} fill={color} />
        <circle cx={cx} cy={cy} r={size * 0.018} fill="#08080e" />

        {/* Score number */}
        <text
          x={cx}
          y={cy + r * 0.25}
          textAnchor="middle"
          dominantBaseline="middle"
          fill={color}
          fontSize={size * 0.22}
          fontFamily="'Space Mono', monospace"
          fontWeight="700"
        >
          {score}
        </text>

        {/* Label below score */}
        <text
          x={cx}
          y={cy + r * 0.60}
          textAnchor="middle"
          dominantBaseline="middle"
          fill="#5c5c7a"
          fontSize={size * 0.08}
          fontFamily="'Space Grotesk', sans-serif"
          fontWeight="500"
          letterSpacing="0.05em"
        >
          {label.toUpperCase()}
        </text>

        {/* Zone labels */}
        <text x={cx - r * 0.85} y={cy + r * 0.25} textAnchor="middle" fill="#10b981" fontSize={size * 0.07} fontFamily="'Space Grotesk', sans-serif">0</text>
        <text x={cx + r * 0.85} y={cy + r * 0.25} textAnchor="middle" fill="#dc2626" fontSize={size * 0.07} fontFamily="'Space Grotesk', sans-serif">100</text>
      </svg>

      <p className="text-xs tracking-widest uppercase" style={{ color: '#5c5c7a' }}>
        Allostatic Score
      </p>
    </div>
  )
}
