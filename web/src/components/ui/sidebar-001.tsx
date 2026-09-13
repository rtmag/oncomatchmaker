// Adapted from 21st.dev · unlumen/sidebar-001 (spring hover highlight, animated active bar, resize)
import { AnimatePresence, motion } from "motion/react"
import * as React from "react"
import { createContext, memo, useCallback, useContext, useMemo, useRef, useState } from "react"

import { cn } from "@/lib/utils"

interface HoverRect {
  top: number
  height: number
  left: number
}

interface HoverContextValue {
  hovered: string | null
  hoverRect: HoverRect | null
  containerRef: React.RefObject<HTMLDivElement | null>
  setHovered: (id: string | null, rect?: HoverRect | null) => void
}

const HoverContext = createContext<HoverContextValue>({
  hovered: null,
  hoverRect: null,
  containerRef: { current: null },
  setHovered: () => {},
})

function HoverProvider({ children, containerRef }: { children: React.ReactNode; containerRef: React.RefObject<HTMLDivElement | null> }) {
  const [hovered, setHoveredId] = useState<string | null>(null)
  const [hoverRect, setHoverRect] = useState<HoverRect | null>(null)
  const setHovered = useCallback((id: string | null, rect?: HoverRect | null) => {
    setHoveredId(id)
    setHoverRect(rect ?? null)
  }, [])
  const value = useMemo(() => ({ hovered, hoverRect, containerRef, setHovered }), [hovered, hoverRect, containerRef, setHovered])
  return <HoverContext.Provider value={value}>{children}</HoverContext.Provider>
}

function HoverHighlight() {
  const { hoverRect, hovered } = useContext(HoverContext)
  return (
    <AnimatePresence>
      {hovered && hoverRect && (
        <motion.div
          key="sb001-hover-bg"
          className="pointer-events-none absolute right-0 z-0 rounded-md bg-accent"
          initial={false}
          animate={{ top: hoverRect.top + 2, height: hoverRect.height - 4, left: hoverRect.left, opacity: 1 }}
          exit={{ opacity: 0 }}
          transition={{ type: "spring", stiffness: 300, damping: 30 }}
        />
      )}
    </AnimatePresence>
  )
}

export interface Sidebar001ItemProps {
  href: string
  label: React.ReactNode
  isActive: boolean
  badge?: React.ReactNode
  className?: string
  onClick?: React.MouseEventHandler<HTMLAnchorElement>
}

export const Sidebar001Item = memo(function Sidebar001Item({ href, label, isActive, badge, className, onClick }: Sidebar001ItemProps) {
  const { hovered, setHovered, containerRef } = useContext(HoverContext)
  const itemRef = useRef<HTMLDivElement>(null)
  const isHovered = hovered === href
  const opacity = isActive ? 1 : hovered !== null ? (isHovered ? 1 : 0.45) : 0.72
  const x = isActive ? 8 : isHovered ? 6 : 0

  const handleMouseEnter = () => {
    const el = itemRef.current
    const container = containerRef.current
    if (!el || !container) return setHovered(href)
    const elRect = el.getBoundingClientRect()
    const containerRect = container.getBoundingClientRect()
    setHovered(href, { top: elRect.top - containerRect.top, height: elRect.height, left: 25 })
  }

  return (
    <div className="relative">
      {isActive && (
        <motion.span
          layoutId="sb001-active-bar"
          className="pointer-events-none absolute left-[4px] top-1/2 z-10 h-[1.8px] -translate-y-1/2 rounded-full bg-primary"
          animate={{ width: 23 }}
          transition={{ type: "spring", stiffness: 800, damping: 40 }}
        />
      )}
      <motion.span
        aria-hidden="true"
        className="pointer-events-none absolute left-0 top-1/2 h-px -translate-y-1/2 bg-foreground/50"
        animate={{ width: isActive ? 0 : isHovered ? 26 : 18 }}
        transition={{ type: "spring", stiffness: 600, damping: 30 }}
      />
      <span aria-hidden="true" className="pointer-events-none absolute left-0 top-1/4 h-px w-[13px] bg-foreground/20" />
      <span aria-hidden="true" className="pointer-events-none absolute left-0 top-3/4 h-px w-[13px] bg-foreground/20" />
      <motion.div
        ref={itemRef}
        animate={{ opacity, x }}
        transition={{ type: "spring", stiffness: 700, damping: 30 }}
        style={{ transformOrigin: "left center" }}
      >
        <a
          href={href}
          onClick={onClick}
          onMouseEnter={handleMouseEnter}
          onMouseLeave={() => setHovered(null)}
          onFocus={handleMouseEnter}
          onBlur={() => setHovered(null)}
          aria-current={isActive ? "page" : undefined}
          className={cn(
            "relative ml-2 flex select-none items-center gap-2.5 rounded-md py-2 pl-4 pr-2 text-sm focus-visible:outline-none",
            isActive ? "text-primary" : "text-foreground",
            className,
          )}
        >
          <span className="relative z-1 flex min-w-0 flex-1 items-center gap-2.5 truncate">{label}</span>
          {badge !== undefined && <span className="relative z-1 text-xs tabular-nums text-muted-foreground">{badge}</span>}
        </a>
      </motion.div>
    </div>
  )
})

export function Sidebar001Section({ label, children, className }: { label?: React.ReactNode; children: React.ReactNode; className?: string }) {
  return (
    <div className={cn("flex flex-col", className)}>
      {label && <div className="mt-2 px-0 py-3.5 text-[11px] font-semibold uppercase tracking-[0.16em] text-foreground/40">{label}</div>}
      {children}
    </div>
  )
}

export function Sidebar001Content({ children, className }: { children: React.ReactNode; className?: string }) {
  const { containerRef } = useContext(HoverContext)
  return (
    <nav aria-label="Workspace" className={cn("no-scrollbar flex-1 overflow-y-auto py-4", className)}>
      <div ref={containerRef} className="relative pl-4 pr-5">
        <HoverHighlight />
        {children}
      </div>
    </nav>
  )
}

export interface Sidebar001Props {
  children: React.ReactNode
  className?: string
  defaultWidth?: number
  minWidth?: number
  maxWidth?: number
}

export function Sidebar001({ children, className, defaultWidth = 248, minWidth = 200, maxWidth = 360 }: Sidebar001Props) {
  const containerRef = useRef<HTMLDivElement>(null)
  const [width, setWidth] = useState(defaultWidth)
  const drag = useRef<{ startX: number; startWidth: number } | null>(null)

  const onPointerDown = (event: React.PointerEvent) => {
    event.preventDefault()
    drag.current = { startX: event.clientX, startWidth: width }
    ;(event.target as HTMLElement).setPointerCapture(event.pointerId)
  }
  const onPointerMove = (event: React.PointerEvent) => {
    if (!drag.current) return
    const next = drag.current.startWidth + event.clientX - drag.current.startX
    setWidth(Math.min(maxWidth, Math.max(minWidth, next)))
  }

  return (
    <HoverProvider containerRef={containerRef}>
      <aside className={cn("relative flex h-full shrink-0 flex-col", className)} style={{ width }}>
        {children}
        <div
          aria-hidden="true"
          className="group/handle absolute right-0 top-0 z-20 h-full w-1 cursor-col-resize"
          onPointerDown={onPointerDown}
          onPointerMove={onPointerMove}
          onPointerUp={() => (drag.current = null)}
        >
          <div className="absolute right-0 top-0 h-full w-px bg-border transition-colors duration-150 group-hover/handle:bg-primary/50" />
        </div>
      </aside>
    </HoverProvider>
  )
}

export function Sidebar001Header({ children, className }: { children?: React.ReactNode; className?: string }) {
  return <div className={cn("shrink-0 px-5 pb-2 pt-7", className)}>{children}</div>
}

export function Sidebar001Footer({ children, className }: { children?: React.ReactNode; className?: string }) {
  return <div className={cn("shrink-0 border-t border-border px-5 pb-5 pt-4", className)}>{children}</div>
}
