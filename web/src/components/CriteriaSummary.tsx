import { CRITERION, CRITERION_ORDER, TONE_TEXT, countCriteria } from "@/lib/status"
import type { Criterion } from "@/lib/types"
import { cn } from "@/lib/utils"

export function CriteriaSummary({ criteria, className }: { criteria: Criterion[]; className?: string }) {
  const counts = countCriteria(criteria)
  return (
    <div className={cn("grid grid-cols-2 gap-3 sm:grid-cols-4", className)}>
      {CRITERION_ORDER.map((status) => (
        <div key={status} className="rounded-xl border border-border bg-card-2 px-4 py-3">
          <div className={cn("font-display text-2xl font-medium tabular-nums", TONE_TEXT[CRITERION[status].tone])}>{counts[status]}</div>
          <div className="mt-0.5 text-xs text-muted-foreground">{CRITERION[status].label}</div>
        </div>
      ))}
    </div>
  )
}
