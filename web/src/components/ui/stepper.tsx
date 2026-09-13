// Adapted from 21st.dev · originui/stepper (lucide icons instead of radix icons)
import { Check, LoaderCircle } from "lucide-react"
import * as React from "react"
import { createContext, useContext } from "react"

import { cn } from "@/lib/utils"

type StepState = "active" | "completed" | "inactive"

interface StepperContextValue {
  activeStep: number
  setActiveStep: (step: number) => void
  orientation: "horizontal" | "vertical"
}

interface StepItemContextValue {
  step: number
  state: StepState
  isDisabled: boolean
  isLoading: boolean
}

const StepperContext = createContext<StepperContextValue | undefined>(undefined)
const StepItemContext = createContext<StepItemContextValue | undefined>(undefined)

function useStepper() {
  const context = useContext(StepperContext)
  if (!context) throw new Error("useStepper must be used within a Stepper")
  return context
}

function useStepItem() {
  const context = useContext(StepItemContext)
  if (!context) throw new Error("useStepItem must be used within a StepperItem")
  return context
}

interface StepperProps extends React.HTMLAttributes<HTMLDivElement> {
  value: number
  onValueChange?: (value: number) => void
  orientation?: "horizontal" | "vertical"
}

export function Stepper({ value, onValueChange, orientation = "horizontal", className, ...props }: StepperProps) {
  const setActiveStep = React.useCallback((step: number) => onValueChange?.(step), [onValueChange])
  return (
    <StepperContext.Provider value={{ activeStep: value, setActiveStep, orientation }}>
      <div
        className={cn(
          "group/stepper inline-flex data-[orientation=horizontal]:w-full data-[orientation=horizontal]:flex-row data-[orientation=vertical]:flex-col",
          className,
        )}
        data-orientation={orientation}
        {...props}
      />
    </StepperContext.Provider>
  )
}

interface StepperItemProps extends React.HTMLAttributes<HTMLDivElement> {
  step: number
  completed?: boolean
  disabled?: boolean
  loading?: boolean
}

export function StepperItem({ step, completed = false, disabled = false, loading = false, className, children, ...props }: StepperItemProps) {
  const { activeStep } = useStepper()
  const state: StepState = completed || step < activeStep ? "completed" : activeStep === step ? "active" : "inactive"
  const isLoading = loading && step === activeStep
  return (
    <StepItemContext.Provider value={{ step, state, isDisabled: disabled, isLoading }}>
      <div
        className={cn(
          "group/step flex items-center group-data-[orientation=horizontal]/stepper:flex-row group-data-[orientation=vertical]/stepper:flex-col",
          className,
        )}
        data-state={state}
        {...(isLoading ? { "data-loading": true } : {})}
        {...props}
      >
        {children}
      </div>
    </StepItemContext.Provider>
  )
}

export function StepperTrigger({ className, children, ...props }: React.ButtonHTMLAttributes<HTMLButtonElement>) {
  const { setActiveStep } = useStepper()
  const { step, isDisabled } = useStepItem()
  return (
    <button
      type="button"
      className={cn("inline-flex items-center gap-3 disabled:pointer-events-none disabled:opacity-50", className)}
      onClick={() => setActiveStep(step)}
      disabled={isDisabled}
      {...props}
    >
      {children}
    </button>
  )
}

export function StepperIndicator({ className, ...props }: React.HTMLAttributes<HTMLDivElement>) {
  const { state, step, isLoading } = useStepItem()
  return (
    <div
      className={cn(
        "relative flex size-6 shrink-0 items-center justify-center rounded-full border border-border-strong bg-card text-xs font-medium text-muted-foreground transition-colors duration-300 data-[state=active]:border-primary data-[state=active]:text-primary data-[state=completed]:border-primary/50 data-[state=completed]:bg-primary/15 data-[state=completed]:text-primary",
        className,
      )}
      data-state={state}
      {...props}
    >
      <span className="transition-all group-data-[loading=true]/step:scale-0 group-data-[state=completed]/step:scale-0 group-data-[loading=true]/step:opacity-0 group-data-[state=completed]/step:opacity-0">
        {step}
      </span>
      <Check
        className="absolute scale-0 opacity-0 transition-all group-data-[state=completed]/step:scale-100 group-data-[state=completed]/step:opacity-100"
        size={14}
        strokeWidth={2.5}
        aria-hidden="true"
      />
      {isLoading && (
        <span className="absolute">
          <LoaderCircle className="animate-spin" size={14} strokeWidth={2} aria-hidden="true" />
        </span>
      )}
    </div>
  )
}

export function StepperTitle({ className, ...props }: React.HTMLAttributes<HTMLHeadingElement>) {
  return <h3 className={cn("text-sm font-medium", className)} {...props} />
}

export function StepperDescription({ className, ...props }: React.HTMLAttributes<HTMLParagraphElement>) {
  return <p className={cn("text-xs text-muted-foreground", className)} {...props} />
}

export function StepperSeparator({ className, ...props }: React.HTMLAttributes<HTMLDivElement>) {
  return (
    <div
      className={cn(
        "m-0.5 bg-border transition-colors duration-500 group-data-[orientation=horizontal]/stepper:h-0.5 group-data-[orientation=vertical]/stepper:h-12 group-data-[orientation=horizontal]/stepper:w-full group-data-[orientation=vertical]/stepper:w-0.5 group-data-[orientation=horizontal]/stepper:flex-1 group-data-[state=completed]/step:bg-primary/60",
        className,
      )}
      {...props}
    />
  )
}
