import { useId, type ReactNode } from "react"

import { cn } from "@/lib/utils"

export const inputClass =
  "h-10 w-full min-w-0 rounded-lg border border-input bg-background/60 px-3 text-sm text-foreground placeholder:text-muted-foreground/60 transition-[border-color,box-shadow] duration-150 focus:border-primary/60 focus:outline-none focus:ring-2 focus:ring-ring/25 aria-[invalid=true]:border-destructive"

interface FieldControlProps {
  id: string
  "aria-invalid": boolean
  "aria-describedby"?: string
}

interface FieldProps {
  label: string
  error?: string
  hint?: string
  className?: string
  children: (control: FieldControlProps) => ReactNode
}

export function Field({ label, error, hint, className, children }: FieldProps) {
  const id = useId()
  const messageId = `${id}-message`
  const message = error ?? hint
  return (
    <div className={cn("grid content-start gap-1.5", className)}>
      <label htmlFor={id} className="text-xs font-medium text-muted-foreground">
        {label}
      </label>
      {children({ id, "aria-invalid": Boolean(error), "aria-describedby": message ? messageId : undefined })}
      {message && (
        <p id={messageId} className={cn("text-xs", error ? "text-destructive" : "text-muted-foreground/80")}>
          {message}
        </p>
      )}
    </div>
  )
}
