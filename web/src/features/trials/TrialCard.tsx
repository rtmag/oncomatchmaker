import { MapPin } from "lucide-react"
import { motion } from "motion/react"

import { AnimatedCircularProgressBar } from "@/components/ui/animated-circular-progress-bar"
import { BorderBeam } from "@/components/ui/border-beam"
import { StatusDot, Tag } from "@/components/ui/surface"
import { routeHref } from "@/hooks/useHashRoute"
import { formatKm, formatPhase } from "@/lib/format"
import { CATEGORY, ELIGIBILITY, TONE_TEXT, TONE_VAR } from "@/lib/status"
import type { RankedTrial } from "@/lib/types"
import { cn } from "@/lib/utils"

const MAX_STAGGER = 8
const EASE_OUT_EXPO = [0.16, 1, 0.3, 1] as const

interface TrialCardProps {
  item: RankedTrial
  index?: number
  featured?: boolean
}

export function TrialCard({ item, index = 0, featured = false }: TrialCardProps) {
  const { trial, match, eligibility, nearest_site: nearest, category } = item
  const categoryMeta = CATEGORY[category]
  const eligibilityMeta = ELIGIBILITY[eligibility.status]
  const summary = trial.interventions.join(" · ") || trial.conditions.join(" · ")

  return (
    <motion.a
      layout
      href={routeHref("trials", trial.nct_id)}
      initial={{ opacity: 0, y: 12 }}
      animate={{ opacity: 1, y: 0 }}
      exit={{ opacity: 0, scale: 0.97 }}
      transition={{ delay: Math.min(index, MAX_STAGGER) * 0.04, duration: 0.35, ease: EASE_OUT_EXPO }}
      className="group relative flex flex-col rounded-2xl border border-border bg-linear-to-br from-card-2 to-card p-5 transition-[border-color,translate,box-shadow] duration-200 hover:-translate-y-0.5 hover:border-primary/40 hover:shadow-lift focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
    >
      {featured && <BorderBeam size={160} duration={10} />}
      <div className="flex items-start justify-between gap-3">
        <div className="flex flex-wrap gap-1.5">
          <Tag tone={categoryMeta.tone}>
            <StatusDot tone={categoryMeta.tone} />
            {categoryMeta.label}
          </Tag>
          <Tag>{formatPhase(trial.phase)}</Tag>
        </div>
        {match.overall_score === null ? (
          <Tag tone={categoryMeta.tone}>Unscored conflict</Tag>
        ) : (
          <AnimatedCircularProgressBar
            value={match.overall_score}
            label={`Clinical match score for ${trial.nct_id}`}
            gaugePrimaryColor={TONE_VAR[categoryMeta.tone]}
            gaugeSecondaryColor="color-mix(in oklab, var(--color-foreground) 9%, transparent)"
            className="-mr-1 -mt-1 size-14 shrink-0 text-base"
          />
        )}
      </div>
      <div className="mt-3 text-[11px] font-medium tabular-nums tracking-[0.14em] text-muted-foreground">{trial.nct_id}</div>
      <h3 className="mt-1.5 line-clamp-3 font-display text-[17px] font-medium leading-snug tracking-tight">{trial.title}</h3>
      {summary && <p className="mt-2 line-clamp-2 text-sm text-muted-foreground">{summary}</p>}
      <div className="mt-auto pt-5">
        <div className="flex items-center justify-between gap-3 border-t border-border pt-4 text-xs">
          <span className="flex min-w-0 items-center gap-1.5 text-muted-foreground">
            <MapPin className="size-3.5 shrink-0" aria-hidden="true" />
            <span className="truncate">
              {nearest ? `${nearest.site.city ?? nearest.site.name} · ${formatKm(nearest.distance_km)}` : "Distance unavailable"}
            </span>
          </span>
          <span className={cn("shrink-0 font-medium", TONE_TEXT[eligibilityMeta.tone])}>{eligibilityMeta.label}</span>
        </div>
      </div>
    </motion.a>
  )
}
