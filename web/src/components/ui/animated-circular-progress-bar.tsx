// Adapted from 21st.dev · dillionverma/animated-circular-progress-bar (rounded label, meter semantics)
import type { ReactNode } from "react"

import { cn } from "@/lib/utils"

interface AnimatedCircularProgressBarProps {
  value: number
  min?: number
  max?: number
  gaugePrimaryColor: string
  gaugeSecondaryColor: string
  className?: string
  /** Accessible name, e.g. "Relevance score". */
  label: string
  children?: ReactNode
}

const RADIUS = 45
const CIRCUMFERENCE = 2 * Math.PI * RADIUS

export function AnimatedCircularProgressBar({
  value,
  min = 0,
  max = 100,
  gaugePrimaryColor,
  gaugeSecondaryColor,
  className,
  label,
  children,
}: AnimatedCircularProgressBarProps) {
  const currentPercent = Math.min(100, Math.max(0, ((value - min) / (max - min)) * 100))
  const circleStyle = {
    "--circle-size": "100px",
    "--circumference": CIRCUMFERENCE,
    "--percent-to-px": `${CIRCUMFERENCE / 100}px`,
    "--gap-percent": "5",
    "--offset-factor": "0",
    "--transition-length": "1s",
    "--delay": "0s",
    "--percent-to-deg": "3.6deg",
    transform: "translateZ(0)",
  } as React.CSSProperties

  return (
    <div
      role="meter"
      aria-label={label}
      aria-valuemin={min}
      aria-valuemax={max}
      aria-valuenow={Math.round(value)}
      className={cn("relative size-40 font-display text-2xl font-medium", className)}
      style={circleStyle}
    >
      <svg fill="none" className="size-full" strokeWidth="2" viewBox="0 0 100 100" aria-hidden="true">
        {currentPercent <= 90 && (
          <circle
            cx="50"
            cy="50"
            r={RADIUS}
            strokeWidth="10"
            strokeDashoffset="0"
            strokeLinecap="round"
            strokeLinejoin="round"
            style={
              {
                stroke: gaugeSecondaryColor,
                "--stroke-percent": 90 - currentPercent,
                "--offset-factor-secondary": "calc(1 - var(--offset-factor))",
                strokeDasharray: "calc(var(--stroke-percent) * var(--percent-to-px)) var(--circumference)",
                transform:
                  "rotate(calc(1turn - 90deg - (var(--gap-percent) * var(--percent-to-deg) * var(--offset-factor-secondary)))) scaleY(-1)",
                transition: "all var(--transition-length) ease var(--delay)",
                transformOrigin: "calc(var(--circle-size) / 2) calc(var(--circle-size) / 2)",
              } as React.CSSProperties
            }
          />
        )}
        <circle
          cx="50"
          cy="50"
          r={RADIUS}
          strokeWidth="10"
          strokeDashoffset="0"
          strokeLinecap="round"
          strokeLinejoin="round"
          style={
            {
              stroke: gaugePrimaryColor,
              "--stroke-percent": currentPercent,
              strokeDasharray: "calc(var(--stroke-percent) * var(--percent-to-px)) var(--circumference)",
              transition: "var(--transition-length) ease var(--delay),stroke var(--transition-length) ease var(--delay)",
              transitionProperty: "stroke-dasharray,transform",
              transform: "rotate(calc(-90deg + var(--gap-percent) * var(--offset-factor) * var(--percent-to-deg)))",
              transformOrigin: "calc(var(--circle-size) / 2) calc(var(--circle-size) / 2)",
            } as React.CSSProperties
          }
        />
      </svg>
      <span className="absolute inset-0 m-auto size-fit tabular-nums">{children ?? Math.round(value)}</span>
    </div>
  )
}
