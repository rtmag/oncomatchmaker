import { motion } from "motion/react"

import { TONE_VAR, type Tone } from "@/lib/status"

export interface PlotSite {
  key: string
  label: string
  lat: number
  lon: number
  tone: Tone
}

interface Coordinate {
  lat: number
  lon: number
}

interface Point {
  key: string
  x: number
  y: number
}

const WIDTH = 720
const HEIGHT = 360
const PAD = 40
const MIN_SPAN_DEG = 8
const GRID_STEPS = [1, 2, 5, 10, 15, 30, 45, 60, 90]
const MAX_GRID_LINES = 8
const MAX_LABELS = 10
const LABEL_BOX = { width: 72, height: 14 }
const ORIGIN_CLEARANCE_PX = 26
const EASE_OUT_EXPO = [0.16, 1, 0.3, 1] as const

function paddedBounds(values: number[], limit: number): [number, number] {
  const lo = Math.min(...values)
  const hi = Math.max(...values)
  const half = (Math.max(hi - lo, MIN_SPAN_DEG) * 1.2) / 2
  const mid = (lo + hi) / 2
  return [Math.max(-limit, mid - half), Math.min(limit, mid + half)]
}

function gridLines(lo: number, hi: number): number[] {
  const step = GRID_STEPS.find((candidate) => (hi - lo) / candidate <= MAX_GRID_LINES) ?? 90
  const start = Math.ceil(lo / step) * step
  const count = Math.max(0, Math.floor((hi - start) / step) + 1)
  return Array.from({ length: count }, (_, index) => start + index * step)
}

/** Greedy placement in distance order: skip labels that would collide with the origin or an earlier label. */
function pickLabels(points: Point[], origin: { x: number; y: number }): Set<string> {
  const placed: Point[] = []
  for (const point of points) {
    if (placed.length === MAX_LABELS) break
    if (Math.hypot(point.x - origin.x, point.y - origin.y) < ORIGIN_CLEARANCE_PX) continue
    const collides = placed.some((other) => Math.abs(other.x - point.x) < LABEL_BOX.width && Math.abs(other.y - point.y) < LABEL_BOX.height)
    if (!collides) placed.push(point)
  }
  return new Set(placed.map((point) => point.key))
}

const formatLon = (lon: number) => `${Math.abs(lon)}°${lon >= 0 ? "E" : "W"}`
const formatLat = (lat: number) => `${Math.abs(lat)}°${lat >= 0 ? "N" : "S"}`

/** Equirectangular sketch: straight-line context only, not a routing or access map. */
export function SitePlot({ origin, sites }: { origin: Coordinate; sites: PlotSite[] }) {
  const [latLo, latHi] = paddedBounds([origin.lat, ...sites.map((s) => s.lat)], 85)
  const [lonLo, lonHi] = paddedBounds([origin.lon, ...sites.map((s) => s.lon)], 180)
  const x = (lon: number) => PAD + ((lon - lonLo) / (lonHi - lonLo)) * (WIDTH - PAD * 2)
  const y = (lat: number) => PAD + ((latHi - lat) / (latHi - latLo)) * (HEIGHT - PAD * 2)
  const ox = x(origin.lon)
  const oy = y(origin.lat)
  const labelled = pickLabels(
    sites.map((site) => ({ key: site.key, x: x(site.lon), y: y(site.lat) })),
    { x: ox, y: oy },
  )

  return (
    <svg viewBox={`0 0 ${WIDTH} ${HEIGHT}`} role="img" aria-label={`Coordinate plot of the patient location and ${sites.length} nearest recruiting sites`} className="h-auto w-full">
      <defs>
        <radialGradient id="origin-glow">
          <stop stopColor="var(--color-primary)" stopOpacity="0.28" />
          <stop offset="1" stopColor="var(--color-primary)" stopOpacity="0" />
        </radialGradient>
      </defs>
      {gridLines(lonLo, lonHi).map((lon) => (
        <g key={`lon-${lon}`}>
          <line x1={x(lon)} x2={x(lon)} y1={PAD} y2={HEIGHT - PAD} className="stroke-border" strokeWidth={0.75} />
          <text x={x(lon)} y={HEIGHT - PAD + 18} textAnchor="middle" className="fill-muted-foreground text-[10px]">
            {formatLon(lon)}
          </text>
        </g>
      ))}
      {gridLines(latLo, latHi).map((lat) => (
        <g key={`lat-${lat}`}>
          <line x1={PAD} x2={WIDTH - PAD} y1={y(lat)} y2={y(lat)} className="stroke-border" strokeWidth={0.75} />
          <text x={PAD - 8} y={y(lat) + 3} textAnchor="end" className="fill-muted-foreground text-[10px]">
            {formatLat(lat)}
          </text>
        </g>
      ))}
      <circle cx={ox} cy={oy} r={80} fill="url(#origin-glow)" />
      {sites.map((site, index) => {
        const sx = x(site.lon)
        const sy = y(site.lat)
        const lift = Math.hypot(sx - ox, sy - oy) * 0.25
        return (
          <motion.path
            key={`arc-${site.key}`}
            d={`M${ox} ${oy} Q${(ox + sx) / 2} ${Math.min(oy, sy) - lift} ${sx} ${sy}`}
            fill="none"
            stroke={TONE_VAR[site.tone]}
            strokeOpacity={0.6}
            strokeWidth={1.25}
            initial={{ pathLength: 0 }}
            animate={{ pathLength: 1 }}
            transition={{ delay: index * 0.06, duration: 0.9, ease: EASE_OUT_EXPO }}
          />
        )
      })}
      {sites.map((site) => (
        <g key={`site-${site.key}`}>
          <circle cx={x(site.lon)} cy={y(site.lat)} r={4.5} fill={TONE_VAR[site.tone]} />
          {labelled.has(site.key) && (
            <text x={x(site.lon) + 9} y={y(site.lat) + 4} className="fill-foreground/85 text-[11px]">
              {site.label}
            </text>
          )}
        </g>
      ))}
      <circle cx={ox} cy={oy} r={12} fill="none" stroke="var(--color-primary)" strokeOpacity={0.45} />
      <circle cx={ox} cy={oy} r={6} fill="var(--color-primary)" />
      <text x={ox} y={oy - 18} textAnchor="middle" className="fill-foreground text-[12px] font-medium">
        Patient
      </text>
    </svg>
  )
}
