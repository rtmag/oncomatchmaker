import * as DialogPrimitive from "@radix-ui/react-dialog"
import { X } from "lucide-react"
import type { ComponentProps, ReactNode } from "react"

import { cn } from "@/lib/utils"

export const Dialog = DialogPrimitive.Root

interface DialogContentProps extends Omit<ComponentProps<typeof DialogPrimitive.Content>, "title"> {
  title: ReactNode
  description?: ReactNode
  eyebrow?: ReactNode
}

export function DialogContent({ className, children, title, description, eyebrow, ...props }: DialogContentProps) {
  return (
    <DialogPrimitive.Portal>
      <DialogPrimitive.Overlay className="dialog-overlay fixed inset-0 z-50 bg-scrim/75 backdrop-blur-sm" />
      <DialogPrimitive.Content
        className={cn(
          "dialog-content fixed left-1/2 top-1/2 z-50 flex max-h-[90vh] w-[min(56rem,94vw)] -translate-x-1/2 -translate-y-1/2 flex-col overflow-hidden rounded-2xl border border-border-strong bg-card shadow-overlay focus:outline-none",
          className,
        )}
        {...props}
      >
        <header className="flex items-start justify-between gap-4 border-b border-border px-6 py-5">
          <div className="min-w-0">
            {eyebrow && <div className="eyebrow mb-2">{eyebrow}</div>}
            <DialogPrimitive.Title className="font-display text-xl font-medium leading-snug tracking-tight">{title}</DialogPrimitive.Title>
            <DialogPrimitive.Description className={cn("mt-1 text-sm text-muted-foreground", !description && "sr-only")}>
              {description ?? "Details"}
            </DialogPrimitive.Description>
          </div>
          <DialogPrimitive.Close className="grid size-9 shrink-0 place-items-center rounded-lg border border-input bg-card-2 text-muted-foreground transition-colors hover:bg-accent hover:text-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring">
            <X className="size-4" />
            <span className="sr-only">Close</span>
          </DialogPrimitive.Close>
        </header>
        <div className="overflow-y-auto px-6 py-6">{children}</div>
      </DialogPrimitive.Content>
    </DialogPrimitive.Portal>
  )
}
