import { ArrowRight, FileSearch, SearchX } from "lucide-react"
import type { ReactNode } from "react"

import { Button } from "@/components/ui/button"
import { routeHref, type View } from "@/hooks/useHashRoute"

interface EmptyStateProps {
  icon: ReactNode
  title: string
  body: string
  actionLabel: string
  actionView: View
}

export function EmptyState({ icon, title, body, actionLabel, actionView }: EmptyStateProps) {
  return (
    <div className="mx-auto flex max-w-lg flex-col items-center py-24 text-center">
      <div className="grid size-14 place-items-center rounded-2xl border border-border-strong bg-card text-primary shadow-lift">{icon}</div>
      <h1 className="mt-6 font-display text-2xl font-medium tracking-tight">{title}</h1>
      <p className="mt-2 text-muted-foreground">{body}</p>
      <Button asChild className="mt-8">
        <a href={routeHref(actionView)}>
          {actionLabel}
          <ArrowRight />
        </a>
      </Button>
    </div>
  )
}

export function NoCaseView() {
  return (
    <EmptyState
      icon={<FileSearch className="size-6" />}
      title="No case loaded yet"
      body="Load a synthetic case, a canonical profile, or a molecular report PDF to open the workspace."
      actionLabel="Start a review"
      actionView="intake"
    />
  )
}

export function NeedsSearch() {
  return (
    <EmptyState
      icon={<SearchX className="size-6" />}
      title="Search not run yet"
      body="Review the profile and confirm it to retrieve treatment evidence and clinical trials."
      actionLabel="Review profile"
      actionView="profile"
    />
  )
}
