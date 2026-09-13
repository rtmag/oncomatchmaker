// Adapted from 21st.dev · dillionverma/number-ticker (motion/react, reduced-motion aware)
import { useMotionValue, useReducedMotion, useSpring } from "motion/react"
import { useCallback, useEffect, useRef } from "react"

import { cn } from "@/lib/utils"

interface NumberTickerProps {
  value: number
  className?: string
  /** Delay in seconds before counting starts. */
  delay?: number
  decimalPlaces?: number
}

export function NumberTicker({ value, className, delay = 0, decimalPlaces = 0 }: NumberTickerProps) {
  const ref = useRef<HTMLSpanElement>(null)
  const reduceMotion = useReducedMotion()
  const motionValue = useMotionValue(0)
  const springValue = useSpring(motionValue, { damping: 60, stiffness: 100 })
  const format = useCallback(
    (n: number) =>
      Intl.NumberFormat("en-US", {
        minimumFractionDigits: decimalPlaces,
        maximumFractionDigits: decimalPlaces,
      }).format(Number(n.toFixed(decimalPlaces))),
    [decimalPlaces],
  )

  // Counts on mount rather than on scroll-into-view: a clinical count must never rest at a wrong value.
  useEffect(() => {
    if (reduceMotion) {
      if (ref.current) ref.current.textContent = format(value)
      return
    }
    const timer = window.setTimeout(() => motionValue.set(value), delay * 1000)
    return () => window.clearTimeout(timer)
  }, [motionValue, delay, value, reduceMotion, format])

  useEffect(
    () =>
      springValue.on("change", (latest) => {
        if (ref.current) ref.current.textContent = format(latest)
      }),
    [springValue, format],
  )

  return (
    <span ref={ref} className={cn("inline-block tabular-nums", className)}>
      {format(0)}
    </span>
  )
}
