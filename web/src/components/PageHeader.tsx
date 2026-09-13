import type { ReactNode } from "react"

import { SOURCE_LABEL } from "@/lib/status"
import { useCase } from "@/state/case-store"

interface PageHeaderProps {
  eyebrow: ReactNode
  title: ReactNode
  subtitle?: ReactNode
  aside?: ReactNode
}

export function PageHeader({ eyebrow, title, subtitle, aside }: PageHeaderProps) {
  return (
    <header className="mb-8 flex flex-wrap items-end justify-between gap-6 sm:mb-10">
      <div className="max-w-3xl">
        <div className="eyebrow">{eyebrow}</div>
        <h1 className="mt-3 text-balance font-display text-[clamp(1.9rem,1.1rem+2.4vw,3.1rem)] font-medium leading-[1.06] tracking-[-0.035em]">
          {title}
        </h1>
        {subtitle && <p className="mt-3 max-w-2xl text-pretty text-[15px] leading-relaxed text-muted-foreground">{subtitle}</p>}
      </div>
      {aside && <div className="shrink-0">{aside}</div>}
    </header>
  )
}

export function CasePill() {
  const { profile, source } = useCase()
  if (!profile) return null
  return (
    <div className="rounded-xl border border-border bg-card/80 px-4 py-2.5 text-sm backdrop-blur">
      <div className="text-[10px] font-semibold uppercase tracking-[0.16em] text-muted-foreground">Review context</div>
      <div className="mt-0.5 font-medium">{profile.disease.normalized || profile.disease.raw_text || "Diagnosis not confirmed"}</div>
      {source && (
        <div className="max-w-64 truncate text-xs text-muted-foreground">
          {SOURCE_LABEL[source.kind]} · {source.label}
        </div>
      )}
    </div>
  )
}
