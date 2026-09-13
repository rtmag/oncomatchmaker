// Adapted from 21st.dev · educalvolpz/animated-tabs (adds counts)
import { motion, useReducedMotion } from "motion/react"
import { useCallback, useId, type KeyboardEvent, type ReactNode } from "react"

import { cn } from "@/lib/utils"

export interface AnimatedTab {
  id: string
  label: string
  icon?: ReactNode
  count?: number
}

interface AnimatedTabsProps {
  tabs: AnimatedTab[]
  activeTab: string
  onChange: (tabId: string) => void
  variant?: "underline" | "pill"
  className?: string
  label?: string
}

const SPRING = { bounce: 0.05, duration: 0.25, type: "spring" as const }

export function AnimatedTabs({ tabs, activeTab, onChange, variant = "pill", className, label = "Tabs" }: AnimatedTabsProps) {
  const reduceMotion = useReducedMotion()
  const layoutId = `animated-tabs-${useId()}`

  const handleKeyDown = useCallback(
    (event: KeyboardEvent, index: number) => {
      const moves: Record<string, number> = {
        ArrowRight: (index + 1) % tabs.length,
        ArrowLeft: (index - 1 + tabs.length) % tabs.length,
        Home: 0,
        End: tabs.length - 1,
      }
      const next = tabs[moves[event.key] ?? -1]
      if (!next) return
      event.preventDefault()
      onChange(next.id)
      document.getElementById(`${layoutId}-tab-${next.id}`)?.focus()
    },
    [tabs, onChange, layoutId],
  )

  return (
    <div
      role="tablist"
      aria-label={label}
      className={cn(
        "relative inline-flex max-w-full overflow-x-auto no-scrollbar",
        variant === "underline" ? "gap-1 border-b border-border" : "gap-1 rounded-full border border-border bg-card p-1",
        className,
      )}
    >
      {tabs.map((tab, index) => {
        const isActive = activeTab === tab.id
        return (
          <button
            key={tab.id}
            id={`${layoutId}-tab-${tab.id}`}
            type="button"
            role="tab"
            aria-selected={isActive}
            tabIndex={isActive ? 0 : -1}
            onClick={() => onChange(tab.id)}
            onKeyDown={(event) => handleKeyDown(event, index)}
            className={cn(
              "relative z-10 flex shrink-0 cursor-pointer items-center justify-center gap-2 px-4 py-2 text-sm font-medium transition-colors",
              "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring",
              variant === "underline" ? "rounded-t-md" : "rounded-full",
              isActive ? "text-primary" : "text-muted-foreground hover:text-foreground",
            )}
          >
            {isActive && (
              <motion.span
                layoutId={layoutId}
                transition={reduceMotion ? { duration: 0 } : SPRING}
                className={cn(
                  "absolute",
                  variant === "underline"
                    ? "inset-x-0 -bottom-px h-0.5 bg-primary"
                    : "inset-0 rounded-full border border-primary/30 bg-primary/12",
                )}
              />
            )}
            {tab.icon ? <span className="relative z-10">{tab.icon}</span> : null}
            <span className="relative z-10">{tab.label}</span>
            {tab.count !== undefined && (
              <span className="relative z-10 rounded-full bg-foreground/8 px-1.5 text-xs tabular-nums">{tab.count}</span>
            )}
          </button>
        )
      })}
    </div>
  )
}
