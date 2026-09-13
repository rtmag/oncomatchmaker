import { AlertTriangle, Info } from "lucide-react"
import type { ComponentProps, ReactNode } from "react"

import type { Tone } from "@/lib/status"
import { cn } from "@/lib/utils"

export function Panel({ className, ...props }: ComponentProps<"section">) {
  return <section className={cn("relative overflow-hidden rounded-2xl border border-border bg-card", className)} {...props} />
}

interface PanelHeaderProps {
  title: ReactNode
  eyebrow?: ReactNode
  description?: ReactNode
  action?: ReactNode
  className?: string
}

export function PanelHeader({ title, eyebrow, description, action, className }: PanelHeaderProps) {
  return (
    <header className={cn("flex items-start justify-between gap-4 px-6 pb-4 pt-6", className)}>
      <div className="min-w-0">
        {eyebrow && <div className="eyebrow mb-1.5">{eyebrow}</div>}
        <h2 className="font-display text-lg font-medium tracking-tight">{title}</h2>
        {description && <p className="mt-1 text-sm text-muted-foreground">{description}</p>}
      </div>
      {action && <div className="shrink-0">{action}</div>}
    </header>
  )
}

const TAG_TONES: Record<Tone, string> = {
  mint: "border-primary/30 bg-primary/10 text-primary",
  evidence: "border-evidence/30 bg-evidence/10 text-evidence",
  caution: "border-caution/35 bg-caution/10 text-caution",
  danger: "border-destructive/35 bg-destructive/10 text-destructive",
  neutral: "border-border-strong bg-foreground/5 text-muted-foreground",
}

export function Tag({ tone = "neutral", className, children }: { tone?: Tone; className?: string; children: ReactNode }) {
  return (
    <span className={cn("inline-flex items-center gap-1.5 whitespace-nowrap rounded-md border px-2 py-0.5 text-xs font-medium", TAG_TONES[tone], className)}>
      {children}
    </span>
  )
}

// Literal class names so Tailwind's scanner generates every tone.
const DOT_TONES: Record<Tone, string> = {
  mint: "bg-primary",
  evidence: "bg-evidence",
  caution: "bg-caution",
  danger: "bg-destructive",
  neutral: "bg-muted-foreground",
}

export function StatusDot({ tone }: { tone: Tone }) {
  return <span aria-hidden="true" className={cn("size-1.5 shrink-0 rounded-full", DOT_TONES[tone])} />
}

export function Callout({ tone = "neutral", title, children, className }: { tone?: "neutral" | "caution"; title?: ReactNode; children: ReactNode; className?: string }) {
  const Icon = tone === "caution" ? AlertTriangle : Info
  return (
    <div
      role={tone === "caution" ? "alert" : undefined}
      className={cn(
        "flex gap-3 rounded-xl border px-4 py-3.5 text-sm",
        tone === "caution" ? "border-caution/30 bg-caution/8 text-caution-foreground" : "border-border-strong bg-card-2 text-muted-foreground",
        className,
      )}
    >
      <Icon className={cn("mt-0.5 size-4 shrink-0", tone === "caution" ? "text-caution" : "text-evidence")} aria-hidden="true" />
      <div className="min-w-0">
        {title && <p className="mb-0.5 font-semibold text-foreground">{title}</p>}
        {children}
      </div>
    </div>
  )
}
