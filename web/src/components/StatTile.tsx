import { NumberTicker } from "@/components/ui/number-ticker"
import { StatusDot } from "@/components/ui/surface"
import type { Tone } from "@/lib/status"

interface StatTileProps {
  label: string
  hint: string
  value: number
  tone: Tone
  delay?: number
}

export function StatTile({ label, hint, value, tone, delay = 0 }: StatTileProps) {
  return (
    <div className="relative overflow-hidden rounded-2xl border border-border bg-card px-5 py-5 transition-colors duration-200 hover:border-border-strong">
      <div className="flex items-start justify-between gap-3">
        <div>
          <div className="text-sm">{label}</div>
          <div className="mt-0.5 text-xs text-muted-foreground">{hint}</div>
        </div>
        <StatusDot tone={tone} />
      </div>
      <NumberTicker value={value} delay={delay} className="mt-6 font-display text-4xl font-medium tracking-tight" />
    </div>
  )
}
