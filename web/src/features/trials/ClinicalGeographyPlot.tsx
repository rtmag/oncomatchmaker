import type { RankedTrial } from "@/lib/types"

const WIDTH = 720
const HEIGHT = 300
const PAD = 42

export function ClinicalGeographyPlot({ trials }: { trials: RankedTrial[] }) {
  const points = trials.filter((trial) => trial.geography_score !== null && trial.match.overall_score !== null)
  const x = (value: number) => PAD + (value / 100) * (WIDTH - PAD * 2)
  const y = (value: number) => HEIGHT - PAD - (value / 100) * (HEIGHT - PAD * 2)

  return (
    <section className="mb-6 rounded-2xl border border-border bg-card p-5">
      <div className="mb-3">
        <h2 className="font-display text-lg font-medium">Clinical match vs geographic access</h2>
        <p className="text-xs text-muted-foreground">Independent 0–100 axes. Upper-right candidates combine stronger clinical review signals with closer confirmed recruiting sites.</p>
      </div>
      {points.length ? (
        <svg viewBox={`0 0 ${WIDTH} ${HEIGHT}`} role="img" aria-label="Clinical match by geographic access plot" className="h-auto w-full">
          <rect x={x(70)} y={y(100)} width={x(100) - x(70)} height={y(50) - y(100)} fill="var(--color-primary)" opacity="0.08" />
          {[0, 25, 50, 75, 100].map((tick) => (
            <g key={tick}>
              <line x1={x(tick)} x2={x(tick)} y1={PAD} y2={HEIGHT - PAD} className="stroke-border" />
              <line x1={PAD} x2={WIDTH - PAD} y1={y(tick)} y2={y(tick)} className="stroke-border" />
              <text x={x(tick)} y={HEIGHT - 14} textAnchor="middle" className="fill-muted-foreground text-[10px]">{tick}</text>
              <text x={24} y={y(tick) + 3} textAnchor="middle" className="fill-muted-foreground text-[10px]">{tick}</text>
            </g>
          ))}
          {points.map((item) => (
            <a key={item.trial.nct_id} href={`#trials/${item.trial.nct_id}`}>
              <circle cx={x(item.match.overall_score ?? 0)} cy={y(item.geography_score ?? 0)} r={7} fill="var(--color-primary)" />
              <text x={x(item.match.overall_score ?? 0) + 10} y={y(item.geography_score ?? 0) + 4} className="fill-foreground text-[10px]">{item.trial.nct_id}</text>
            </a>
          ))}
          <text x={WIDTH / 2} y={HEIGHT - 1} textAnchor="middle" className="fill-muted-foreground text-[11px]">Clinical match score</text>
          <text transform={`translate(10 ${HEIGHT / 2}) rotate(-90)`} textAnchor="middle" className="fill-muted-foreground text-[11px]">Geographic access score</text>
        </svg>
      ) : (
        <p className="text-sm text-muted-foreground">No candidate currently has a confirmed recruiting site with calculable distance.</p>
      )}
    </section>
  )
}
